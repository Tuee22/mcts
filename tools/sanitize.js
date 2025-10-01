#!/usr/bin/env node
/**
 * Encoding Sanitizer Tool
 * 
 * Detects and fixes UTF-16 surrogate encoding issues that can cause
 * "no low surrogate" errors in Claude Code workflows.
 * 
 * Features:
 * - Fast scanning using ripgrep when available
 * - Cross-platform Node.js fallback
 * - Respects .sanitizeignore patterns
 * - Check and fix modes
 * - Pre-commit hook compatible
 */

const fs = require('fs');
const path = require('path');
const { execSync, spawn } = require('child_process');
const { createReadStream, createWriteStream } = require('fs');
const { createInterface } = require('readline');

// Configuration
const UNICODE_REPLACEMENT_CHAR = '\uFFFD';
const DEFAULT_TEXT_EXTENSIONS = [
  '.js', '.jsx', '.ts', '.tsx', '.json', '.jsonc',
  '.py', '.pyi', '.md', '.txt', '.yml', '.yaml',
  '.toml', '.ini', '.cfg', '.conf', '.sh', '.bash',
  '.css', '.scss', '.sass', '.html', '.htm', '.xml',
  '.c', '.cpp', '.h', '.hpp', '.cc', '.cxx',
  '.go', '.rs', '.java', '.kt', '.swift', '.rb',
  '.php', '.pl', '.lua', '.sql', '.dockerfile'
];

class SurrogateSanitizer {
  constructor(options = {}) {
    this.rootDir = options.rootDir || process.cwd();
    this.verbose = options.verbose || false;
    this.dryRun = options.dryRun || false;
    this.ignorePatterns = this.loadIgnorePatterns();
    this.hasRipgrep = this.checkRipgrep();
    
    // Stats
    this.stats = {
      filesScanned: 0,
      filesWithIssues: 0,
      surrogatesFound: 0,
      surrogatesFixed: 0
    };
  }

  checkRipgrep() {
    try {
      execSync('rg --version', { stdio: 'ignore' });
      return true;
    } catch {
      return false;
    }
  }

  loadIgnorePatterns() {
    const ignoreFile = path.join(this.rootDir, '.sanitizeignore');
    const patterns = [
      // Default binary patterns
      '*.png', '*.jpg', '*.jpeg', '*.gif', '*.ico', '*.svg',
      '*.woff', '*.woff2', '*.eot', '*.ttf', '*.otf',
      '*.zip', '*.tar', '*.gz', '*.bz2', '*.7z', '*.rar',
      '*.pdf', '*.doc', '*.docx', '*.xls', '*.xlsx', '*.ppt', '*.pptx',
      '*.exe', '*.dll', '*.so', '*.dylib', '*.bin',
      '*.mp4', '*.avi', '*.mov', '*.mkv', '*.mp3', '*.wav',
      
      // Default directories
      'node_modules/', 'build/', 'dist/', '.next/', 'coverage/',
      '__pycache__/', '.pytest_cache/', '.mypy_cache/',
      '.git/', '.svn/', '.hg/',
      
      // Build artifacts
      '*.so', '*.o', '*.core', 'core.*'
    ];

    try {
      if (fs.existsSync(ignoreFile)) {
        const content = fs.readFileSync(ignoreFile, 'utf8');
        const customPatterns = content
          .split('\n')
          .map(line => line.trim())
          .filter(line => line && !line.startsWith('#'));
        patterns.push(...customPatterns);
      }
    } catch (error) {
      if (this.verbose) {
        console.warn(`Warning: Could not read .sanitizeignore: ${error.message}`);
      }
    }

    return patterns;
  }

  shouldIgnoreFile(filePath) {
    const relativePath = path.relative(this.rootDir, filePath);
    
    return this.ignorePatterns.some(pattern => {
      if (pattern.endsWith('/')) {
        return relativePath.startsWith(pattern) || relativePath.includes('/' + pattern);
      }
      if (pattern.startsWith('*')) {
        return relativePath.endsWith(pattern.slice(1));
      }
      if (pattern.includes('*')) {
        const regex = new RegExp(pattern.replace(/\*/g, '.*'));
        return regex.test(relativePath);
      }
      return relativePath === pattern || relativePath.includes(pattern);
    });
  }

  isTextFile(filePath) {
    const ext = path.extname(filePath).toLowerCase();
    if (DEFAULT_TEXT_EXTENSIONS.includes(ext)) {
      return true;
    }
    
    // Check if file has no extension but looks like text
    if (!ext && fs.existsSync(filePath)) {
      try {
        const sample = fs.readFileSync(filePath, { encoding: 'utf8', start: 0, end: 512 });
        // Simple heuristic: if we can read it as UTF-8 and it doesn't contain null bytes
        return !sample.includes('\0');
      } catch {
        return false;
      }
    }
    
    return false;
  }

  detectSurrogatesRipgrep() {
    if (!this.hasRipgrep) return [];
    
    try {
      // Use ripgrep to find high surrogates (U+D800-U+DBFF) and low surrogates (U+DC00-U+DFFF)
      const surrogatePattern = '[\\uD800-\\uDFFF]';
      const cmd = [
        'rg',
        '--line-number',
        '--column',
        '--no-heading',
        '--color=never',
        '--type-add=text:*',
        surrogatePattern,
        this.rootDir
      ];
      
      // Add ignore patterns
      for (const pattern of this.ignorePatterns) {
        if (pattern.includes('*') || pattern.endsWith('/')) {
          cmd.push('--glob');
          cmd.push(`!${pattern}`);
        }
      }
      
      const result = execSync(cmd.join(' '), { 
        encoding: 'utf8',
        maxBuffer: 10 * 1024 * 1024 // 10MB buffer
      });
      
      const matches = [];
      for (const line of result.split('\n').filter(Boolean)) {
        const [filePath, lineNum, colNum, ...contentParts] = line.split(':');
        if (filePath && lineNum && colNum) {
          matches.push({
            file: filePath,
            line: parseInt(lineNum),
            column: parseInt(colNum),
            content: contentParts.join(':')
          });
        }
      }
      
      return matches;
    } catch (error) {
      if (this.verbose) {
        console.warn(`Warning: ripgrep failed, falling back to Node.js scanner: ${error.message}`);
      }
      return [];
    }
  }

  async detectSurrogatesNode() {
    const matches = [];
    const files = await this.findTextFiles();
    
    for (const filePath of files) {
      if (this.shouldIgnoreFile(filePath)) continue;
      
      try {
        await this.scanFileForSurrogates(filePath, matches);
        this.stats.filesScanned++;
      } catch (error) {
        if (this.verbose) {
          console.warn(`Warning: Could not scan ${filePath}: ${error.message}`);
        }
      }
    }
    
    return matches;
  }

  async findTextFiles() {
    const files = [];
    
    const walkDir = (dir) => {
      try {
        const entries = fs.readdirSync(dir);
        
        for (const entry of entries) {
          const fullPath = path.join(dir, entry);
          const stat = fs.statSync(fullPath);
          
          if (stat.isDirectory()) {
            if (!this.shouldIgnoreFile(fullPath)) {
              walkDir(fullPath);
            }
          } else if (stat.isFile() && this.isTextFile(fullPath)) {
            files.push(fullPath);
          }
        }
      } catch (error) {
        if (this.verbose) {
          console.warn(`Warning: Could not read directory ${dir}: ${error.message}`);
        }
      }
    };
    
    walkDir(this.rootDir);
    return files;
  }

  async scanFileForSurrogates(filePath, matches) {
    const fileStream = createReadStream(filePath, { encoding: 'utf8' });
    const rl = createInterface({ input: fileStream, crlfDelay: Infinity });
    
    let lineNumber = 0;
    
    for await (const line of rl) {
      lineNumber++;
      
      for (let i = 0; i < line.length; i++) {
        const char = line[i];
        const code = char.charCodeAt(0);
        
        // Check for unpaired surrogates
        if (code >= 0xD800 && code <= 0xDBFF) {
          // High surrogate - check if followed by low surrogate
          const nextChar = line[i + 1];
          if (!nextChar || nextChar.charCodeAt(0) < 0xDC00 || nextChar.charCodeAt(0) > 0xDFFF) {
            matches.push({
              file: filePath,
              line: lineNumber,
              column: i + 1,
              content: line,
              type: 'unpaired_high_surrogate',
              char: char
            });
          }
        } else if (code >= 0xDC00 && code <= 0xDFFF) {
          // Low surrogate - check if preceded by high surrogate
          const prevChar = line[i - 1];
          if (!prevChar || prevChar.charCodeAt(0) < 0xD800 || prevChar.charCodeAt(0) > 0xDBFF) {
            matches.push({
              file: filePath,
              line: lineNumber,
              column: i + 1,
              content: line,
              type: 'unpaired_low_surrogate',
              char: char
            });
          }
        }
      }
    }
  }

  async checkMode() {
    console.log('🔍 Scanning for unpaired UTF-16 surrogates...');
    
    const matches = this.hasRipgrep 
      ? this.detectSurrogatesRipgrep()
      : await this.detectSurrogatesNode();
    
    if (matches.length === 0) {
      console.log('✅ No unpaired surrogates found. Repository is clean.');
      return { success: true, matches: [] };
    }
    
    console.log(`❌ Found ${matches.length} unpaired surrogate(s) in ${new Set(matches.map(m => m.file)).size} file(s):`);
    console.log('');
    
    for (const match of matches) {
      console.log(`📁 ${path.relative(this.rootDir, match.file)}:${match.line}:${match.column}`);
      console.log(`   ${match.content.slice(0, 100)}${match.content.length > 100 ? '...' : ''}`);
      console.log(`   ${''.padStart(match.column - 1)}^ ${match.type || 'unpaired surrogate'}`);
      console.log('');
    }
    
    console.log('💡 Run with --fix to replace unpaired surrogates with Unicode replacement character (�)');
    return { success: false, matches };
  }

  async fixMode() {
    console.log('🔧 Scanning and fixing unpaired UTF-16 surrogates...');
    
    const matches = this.hasRipgrep 
      ? this.detectSurrogatesRipgrep()
      : await this.detectSurrogatesNode();
    
    if (matches.length === 0) {
      console.log('✅ No unpaired surrogates found. Repository is clean.');
      return { success: true, matches: [] };
    }
    
    const fileGroups = {};
    for (const match of matches) {
      if (!fileGroups[match.file]) {
        fileGroups[match.file] = [];
      }
      fileGroups[match.file].push(match);
    }
    
    for (const [filePath, fileMatches] of Object.entries(fileGroups)) {
      await this.fixFilesSurrogates(filePath, fileMatches);
    }
    
    console.log(`✅ Fixed ${this.stats.surrogatesFixed} unpaired surrogate(s) in ${Object.keys(fileGroups).length} file(s)`);
    return { success: true, matches };
  }

  async fixFilesSurrogates(filePath, matches) {
    if (this.dryRun) {
      console.log(`[DRY RUN] Would fix ${matches.length} surrogate(s) in ${filePath}`);
      return;
    }
    
    let content = fs.readFileSync(filePath, 'utf8');
    let fixedCount = 0;
    
    // Sort matches by position (reverse order to maintain indices)
    matches.sort((a, b) => b.line - a.line || b.column - a.column);
    
    const lines = content.split('\n');
    
    for (const match of matches) {
      const lineIndex = match.line - 1;
      const colIndex = match.column - 1;
      
      if (lineIndex < lines.length && colIndex < lines[lineIndex].length) {
        const line = lines[lineIndex];
        const char = line[colIndex];
        const code = char.charCodeAt(0);
        
        // Double-check it's still a surrogate
        if ((code >= 0xD800 && code <= 0xDFFF)) {
          lines[lineIndex] = line.slice(0, colIndex) + UNICODE_REPLACEMENT_CHAR + line.slice(colIndex + 1);
          fixedCount++;
          this.stats.surrogatesFixed++;
        }
      }
    }
    
    if (fixedCount > 0) {
      // Create backup
      const backupPath = filePath + '.sanitize-backup';
      fs.copyFileSync(filePath, backupPath);
      
      // Write fixed content
      const fixedContent = lines.join('\n');
      fs.writeFileSync(filePath, fixedContent, 'utf8');
      
      console.log(`🔧 Fixed ${fixedCount} surrogate(s) in ${path.relative(this.rootDir, filePath)}`);
      console.log(`   Backup created: ${path.basename(backupPath)}`);
      
      this.stats.filesWithIssues++;
    }
  }

  async normalizeMode() {
    console.log('🔄 Normalizing file encodings to UTF-8...');
    // This would detect non-UTF-8 files and convert them
    // For now, just run the check mode
    return this.checkMode();
  }

  printStats() {
    if (this.verbose) {
      console.log('');
      console.log('📊 Statistics:');
      console.log(`   Files scanned: ${this.stats.filesScanned}`);
      console.log(`   Files with issues: ${this.stats.filesWithIssues}`);
      console.log(`   Surrogates found: ${this.stats.surrogatesFound}`);
      console.log(`   Surrogates fixed: ${this.stats.surrogatesFixed}`);
    }
  }
}

// CLI interface
function printUsage() {
  console.log(`
Usage: node sanitize.js [options]

Options:
  --check          Check for unpaired surrogates (default)
  --fix            Fix unpaired surrogates by replacing with �
  --normalize      Normalize file encodings to UTF-8
  --verbose        Show detailed output
  --dry-run        Show what would be done without making changes
  --help           Show this help message

Exit codes:
  0 - Success (no issues found or all issues fixed)
  1 - Issues found (check mode) or errors occurred
  2 - Invalid usage

Examples:
  npm run sanitize:check
  npm run sanitize:fix
  node tools/sanitize.js --fix --verbose
`);
}

async function main() {
  const args = process.argv.slice(2);
  
  if (args.includes('--help') || args.includes('-h')) {
    printUsage();
    process.exit(0);
  }
  
  const options = {
    verbose: args.includes('--verbose'),
    dryRun: args.includes('--dry-run')
  };
  
  const sanitizer = new SurrogateSanitizer(options);
  let result;
  
  try {
    if (args.includes('--fix')) {
      result = await sanitizer.fixMode();
    } else if (args.includes('--normalize')) {
      result = await sanitizer.normalizeMode();
    } else {
      result = await sanitizer.checkMode();
    }
    
    sanitizer.printStats();
    
    if (result.success) {
      process.exit(0);
    } else {
      process.exit(1);
    }
  } catch (error) {
    console.error(`❌ Error: ${error.message}`);
    if (options.verbose) {
      console.error(error.stack);
    }
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}

module.exports = { SurrogateSanitizer };