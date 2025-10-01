#!/usr/bin/env node
/**
 * Payload Size Guard for Claude Code
 * 
 * Prevents oversized payloads that could cause transport issues or
 * "no low surrogate" errors by implementing size limits and auto-chunking.
 * 
 * Features:
 * - Size estimation for Claude Code requests
 * - Auto-chunking by file patterns
 * - Configuration override mechanisms
 * - Clear warnings and recommendations
 */

const fs = require('fs');
const path = require('path');
const { stripUnpairedSurrogates, getUtf8ByteLength, safeTruncate } = require('./string-utils');

// Configuration constants
const DEFAULT_MAX_PAYLOAD_SIZE = 200 * 1024; // 200KB
const DEFAULT_WARNING_THRESHOLD = 150 * 1024; // 150KB  
const DEFAULT_CHUNK_SIZE = 100 * 1024; // 100KB
const SAFETY_BUFFER = 10 * 1024; // 10KB safety buffer

class PayloadGuard {
  constructor(options = {}) {
    this.rootDir = options.rootDir || process.cwd();
    this.maxPayloadSize = options.maxPayloadSize || DEFAULT_MAX_PAYLOAD_SIZE;
    this.warningThreshold = options.warningThreshold || DEFAULT_WARNING_THRESHOLD;
    this.maxChunkSize = options.maxChunkSize || DEFAULT_CHUNK_SIZE;
    this.verbose = options.verbose || false;
    this.dryRun = options.dryRun || false;
    
    // Load configuration
    this.loadConfiguration();
    
    // File patterns for chunking
    this.chunkPatterns = {
      frontend: ['frontend/src/**/*.{js,jsx,ts,tsx}', 'frontend/tests/**/*.{js,jsx,ts,tsx}'],
      backend: ['backend/**/*.py', 'tests/**/*.py'],
      docs: ['docs/**/*.md', '*.md'],
      config: ['*.json', '*.yaml', '*.yml', '*.toml'],
      tools: ['tools/**/*'],
      tests: ['tests/**/*', 'frontend/tests/**/*']
    };
  }

  loadConfiguration() {
    try {
      const configPath = path.join(this.rootDir, '.claude', 'payload-config.json');
      if (fs.existsSync(configPath)) {
        const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
        this.maxPayloadSize = config.maxPayloadSize || this.maxPayloadSize;
        this.warningThreshold = config.warningThreshold || this.warningThreshold;
        this.maxChunkSize = config.maxChunkSize || this.maxChunkSize;
        if (config.chunkPatterns) {
          Object.assign(this.chunkPatterns, config.chunkPatterns);
        }
      }
    } catch (error) {
      if (this.verbose) {
        console.warn(`Warning: Could not load payload configuration: ${error.message}`);
      }
    }
  }

  /**
   * Estimate the size of a potential Claude Code request
   * @param {Object} requestData - Request data to estimate
   * @returns {Object} Size estimation results
   */
  estimateRequestSize(requestData = {}) {
    let totalSize = 0;
    const breakdown = {};
    
    // Context and system prompts (estimated)
    const contextEstimate = 5000; // Rough estimate for context
    totalSize += contextEstimate;
    breakdown.context = contextEstimate;
    
    // Files that might be read
    if (requestData.files) {
      let filesSize = 0;
      for (const filePath of requestData.files) {
        try {
          if (fs.existsSync(filePath)) {
            const content = fs.readFileSync(filePath, 'utf8');
            const sanitizedContent = stripUnpairedSurrogates(content);
            const fileSize = getUtf8ByteLength(sanitizedContent);
            filesSize += fileSize;
            
            if (this.verbose) {
              console.log(`File ${filePath}: ${fileSize} bytes`);
            }
          }
        } catch (error) {
          if (this.verbose) {
            console.warn(`Warning: Could not read ${filePath}: ${error.message}`);
          }
        }
      }
      totalSize += filesSize;
      breakdown.files = filesSize;
    }
    
    // User prompt
    if (requestData.prompt) {
      const promptSize = getUtf8ByteLength(stripUnpairedSurrogates(requestData.prompt));
      totalSize += promptSize;
      breakdown.prompt = promptSize;
    }
    
    // Bash output (if captured)
    if (requestData.bashOutput) {
      const bashSize = getUtf8ByteLength(stripUnpairedSurrogates(requestData.bashOutput));
      totalSize += bashSize;
      breakdown.bashOutput = bashSize;
    }
    
    // Safety buffer for protocol overhead
    totalSize += SAFETY_BUFFER;
    breakdown.overhead = SAFETY_BUFFER;
    
    return {
      totalSize,
      breakdown,
      exceedsWarning: totalSize > this.warningThreshold,
      exceedsLimit: totalSize > this.maxPayloadSize
    };
  }

  /**
   * Find text files in the repository for size estimation
   * @returns {Array} Array of file paths
   */
  findTextFiles() {
    const files = [];
    const textExtensions = ['.js', '.jsx', '.ts', '.tsx', '.json', '.py', '.md', '.txt', '.yml', '.yaml'];
    
    const walkDir = (dir) => {
      try {
        const entries = fs.readdirSync(dir);
        
        for (const entry of entries) {
          const fullPath = path.join(dir, entry);
          const stat = fs.statSync(fullPath);
          
          if (stat.isDirectory()) {
            // Skip known large directories
            if (!['node_modules', 'build', 'dist', '.next', 'coverage', '__pycache__'].includes(entry)) {
              walkDir(fullPath);
            }
          } else if (stat.isFile()) {
            const ext = path.extname(fullPath).toLowerCase();
            if (textExtensions.includes(ext)) {
              files.push(fullPath);
            }
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

  /**
   * Generate file chunks based on patterns and size limits
   * @param {Array} files - Array of file paths
   * @returns {Array} Array of chunk objects
   */
  generateChunks(files) {
    const chunks = [];
    const filesByPattern = {};
    
    // Group files by pattern
    for (const [patternName, patterns] of Object.entries(this.chunkPatterns)) {
      filesByPattern[patternName] = [];
      
      for (const file of files) {
        const relativePath = path.relative(this.rootDir, file);
        
        // Simple pattern matching
        for (const pattern of patterns) {
          const regex = new RegExp(
            pattern
              .replace(/\*\*/g, '.*')
              .replace(/\*/g, '[^/]*')
              .replace(/\{([^}]+)\}/g, '($1)')
              .replace(/,/g, '|')
          );
          
          if (regex.test(relativePath)) {
            filesByPattern[patternName].push(file);
            break;
          }
        }
      }
    }
    
    // Create chunks for each pattern
    for (const [patternName, patternFiles] of Object.entries(filesByPattern)) {
      if (patternFiles.length === 0) continue;
      
      let currentChunk = {
        name: `${patternName}-chunk-1`,
        pattern: patternName,
        files: [],
        estimatedSize: SAFETY_BUFFER
      };
      
      let chunkIndex = 1;
      
      for (const file of patternFiles) {
        try {
          const stat = fs.statSync(file);
          const estimatedFileSize = Math.min(stat.size, stat.size * 1.2); // Account for UTF-8 encoding
          
          // If adding this file would exceed chunk limit, start new chunk
          if (currentChunk.estimatedSize + estimatedFileSize > this.maxChunkSize && currentChunk.files.length > 0) {
            chunks.push(currentChunk);
            chunkIndex++;
            currentChunk = {
              name: `${patternName}-chunk-${chunkIndex}`,
              pattern: patternName,
              files: [],
              estimatedSize: SAFETY_BUFFER
            };
          }
          
          currentChunk.files.push(file);
          currentChunk.estimatedSize += estimatedFileSize;
          
        } catch (error) {
          if (this.verbose) {
            console.warn(`Warning: Could not stat ${file}: ${error.message}`);
          }
        }
      }
      
      // Add the last chunk if it has files
      if (currentChunk.files.length > 0) {
        chunks.push(currentChunk);
      }
    }
    
    return chunks;
  }

  /**
   * Check the current repository for payload size issues
   * @returns {Object} Check results
   */
  async checkPayloadSize() {
    console.log('📏 Analyzing repository payload size for Claude Code...');
    
    const files = this.findTextFiles();
    const estimation = this.estimateRequestSize({ files });
    
    console.log('');
    console.log('📊 Payload Size Analysis:');
    console.log(`   Total estimated size: ${this.formatBytes(estimation.totalSize)}`);
    console.log(`   Warning threshold: ${this.formatBytes(this.warningThreshold)}`);
    console.log(`   Maximum limit: ${this.formatBytes(this.maxPayloadSize)}`);
    console.log('');
    
    if (estimation.breakdown) {
      console.log('📋 Size breakdown:');
      for (const [category, size] of Object.entries(estimation.breakdown)) {
        console.log(`   ${category}: ${this.formatBytes(size)}`);
      }
      console.log('');
    }
    
    if (estimation.exceedsLimit) {
      console.log('❌ Repository exceeds maximum payload size limit');
      console.log('');
      console.log('🔧 Recommended actions:');
      console.log('   1. Use auto-chunking: npm run ai:plan --chunk');
      console.log('   2. Exclude large directories in .claude/settings.local.json');
      console.log('   3. Use session management: npm run ai:session:new');
      console.log('');
      
      return { success: false, ...estimation };
    }
    
    if (estimation.exceedsWarning) {
      console.log('⚠️  Repository size exceeds warning threshold');
      console.log('');
      console.log('💡 Consider using chunking or session management for better performance');
      console.log('');
      
      return { success: true, warning: true, ...estimation };
    }
    
    console.log('✅ Repository size is within safe limits');
    return { success: true, warning: false, ...estimation };
  }

  /**
   * Generate chunking recommendations
   * @returns {Object} Chunking recommendations
   */
  generateChunkingStrategy() {
    console.log('🧩 Generating chunking strategy...');
    
    const files = this.findTextFiles();
    const chunks = this.generateChunks(files);
    
    console.log('');
    console.log(`Generated ${chunks.length} chunks:`);
    
    for (const chunk of chunks) {
      console.log('');
      console.log(`📦 ${chunk.name}:`);
      console.log(`   Pattern: ${chunk.pattern}`);
      console.log(`   Files: ${chunk.files.length}`);
      console.log(`   Estimated size: ${this.formatBytes(chunk.estimatedSize)}`);
      
      if (this.verbose) {
        console.log(`   Files:`);
        for (const file of chunk.files.slice(0, 5)) {
          console.log(`     - ${path.relative(this.rootDir, file)}`);
        }
        if (chunk.files.length > 5) {
          console.log(`     ... and ${chunk.files.length - 5} more`);
        }
      }
    }
    
    console.log('');
    console.log('📝 Usage instructions:');
    console.log('   Create separate Claude sessions for each chunk');
    console.log('   Focus on one logical area at a time');
    console.log('   Use cross-references between sessions if needed');
    
    return { chunks, totalFiles: files.length };
  }

  formatBytes(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  }
}

// CLI interface
function printUsage() {
  console.log(`
Usage: node payload-guard.js [options]

Options:
  --check          Check current payload size (default)
  --chunk          Generate chunking strategy
  --config         Show current configuration
  --set-limit N    Set maximum payload size (bytes)
  --verbose        Show detailed output
  --help           Show this help message

Examples:
  npm run ai:plan
  node tools/payload-guard.js --chunk
  node tools/payload-guard.js --set-limit 300000
`);
}

async function main() {
  const args = process.argv.slice(2);
  
  if (args.includes('--help') || args.includes('-h')) {
    printUsage();
    process.exit(0);
  }
  
  const options = {
    verbose: args.includes('--verbose')
  };
  
  // Handle --set-limit
  const limitIndex = args.indexOf('--set-limit');
  if (limitIndex !== -1 && args[limitIndex + 1]) {
    const newLimit = parseInt(args[limitIndex + 1]);
    if (isNaN(newLimit) || newLimit <= 0) {
      console.error('❌ Invalid limit value');
      process.exit(1);
    }
    options.maxPayloadSize = newLimit;
  }
  
  const guard = new PayloadGuard(options);
  
  try {
    if (args.includes('--chunk')) {
      const result = guard.generateChunkingStrategy();
      console.log(`✅ Generated chunking strategy with ${result.chunks.length} chunks`);
    } else if (args.includes('--config')) {
      console.log('⚙️  Current configuration:');
      console.log(`   Max payload size: ${guard.formatBytes(guard.maxPayloadSize)}`);
      console.log(`   Warning threshold: ${guard.formatBytes(guard.warningThreshold)}`);
      console.log(`   Max chunk size: ${guard.formatBytes(guard.maxChunkSize)}`);
    } else {
      const result = await guard.checkPayloadSize();
      if (!result.success) {
        process.exit(1);
      }
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

module.exports = { PayloadGuard };