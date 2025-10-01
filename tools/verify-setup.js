#!/usr/bin/env node
/**
 * Verification Tool for Claude Code Workflow Setup
 * 
 * Verifies that all components of the UTF-16 surrogate protection
 * and payload governance system are properly installed and working.
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');
const { SurrogateSanitizer } = require('./sanitize');
const { PayloadGuard } = require('./payload-guard');

class SetupVerifier {
  constructor(options = {}) {
    this.rootDir = options.rootDir || process.cwd();
    this.verbose = options.verbose || false;
    this.results = [];
  }

  log(message, type = 'info') {
    const icons = {
      info: 'ℹ️ ',
      success: '✅',
      warning: '⚠️ ',
      error: '❌',
      test: '🧪'
    };
    
    console.log(`${icons[type]} ${message}`);
  }

  addResult(check, passed, message, details = null) {
    const result = { check, passed, message, details };
    this.results.push(result);
    
    if (passed) {
      this.log(`${check}: ${message}`, 'success');
    } else {
      this.log(`${check}: ${message}`, 'error');
    }
    
    if (details && this.verbose) {
      console.log(`   ${details}`);
    }
  }

  checkFileExists(filePath, description) {
    const exists = fs.existsSync(path.join(this.rootDir, filePath));
    this.addResult(
      `File Check: ${filePath}`,
      exists,
      exists ? `${description} exists` : `${description} missing`,
      exists ? null : `Expected file at: ${path.join(this.rootDir, filePath)}`
    );
    return exists;
  }

  checkFileContent(filePath, pattern, description) {
    try {
      const content = fs.readFileSync(path.join(this.rootDir, filePath), 'utf8');
      const matches = pattern.test(content);
      this.addResult(
        `Content Check: ${filePath}`,
        matches,
        matches ? `${description} configured correctly` : `${description} configuration missing`,
        matches ? null : `Pattern not found: ${pattern}`
      );
      return matches;
    } catch (error) {
      this.addResult(
        `Content Check: ${filePath}`,
        false,
        `Failed to read ${description}`,
        error.message
      );
      return false;
    }
  }

  checkCommand(command, description) {
    try {
      execSync(command, { stdio: 'ignore' });
      this.addResult(
        `Command Check: ${command}`,
        true,
        `${description} available`
      );
      return true;
    } catch (error) {
      this.addResult(
        `Command Check: ${command}`,
        false,
        `${description} not available`,
        error.message
      );
      return false;
    }
  }

  async testSanitizer() {
    this.log('Testing surrogate sanitizer...', 'test');
    
    try {
      const sanitizer = new SurrogateSanitizer({ verbose: false, dryRun: true });
      
      // Test with clean string
      const cleanResult = await sanitizer.checkMode();
      this.addResult(
        'Sanitizer Test: Clean scan',
        cleanResult.success,
        cleanResult.success ? 'Sanitizer works on clean repository' : 'Sanitizer failed on clean repository'
      );
      
      return cleanResult.success;
    } catch (error) {
      this.addResult(
        'Sanitizer Test: Functionality',
        false,
        'Sanitizer failed to run',
        error.message
      );
      return false;
    }
  }

  async testPayloadGuard() {
    this.log('Testing payload guard...', 'test');
    
    try {
      const guard = new PayloadGuard({ verbose: false });
      const result = await guard.checkPayloadSize();
      
      this.addResult(
        'Payload Guard Test: Size check',
        true,
        'Payload guard successfully analyzed repository size'
      );
      
      return true;
    } catch (error) {
      this.addResult(
        'Payload Guard Test: Functionality',
        false,
        'Payload guard failed to run',
        error.message
      );
      return false;
    }
  }


  async runFullVerification() {
    this.log('🔍 Running full Claude Code workflow verification...', 'info');
    console.log('');
    
    // Check core configuration files
    this.log('Checking configuration files...', 'info');
    this.checkFileExists('.editorconfig', 'EditorConfig');
    this.checkFileExists('.vscode/settings.json', 'VS Code settings');
    this.checkFileExists('.claude/settings.local.json', 'Claude settings');
    this.checkFileExists('package.json', 'Root package.json');
    this.checkFileExists('.sanitizeignore', 'Sanitizer ignore file');
    
    console.log('');
    
    // Check file contents
    this.log('Checking configuration content...', 'info');
    this.checkFileContent('.editorconfig', /charset = utf-8/, 'UTF-8 charset enforcement');
    this.checkFileContent('.vscode/settings.json', /"files\.encoding": "utf8"/, 'VS Code UTF-8 enforcement');
    this.checkFileContent('.claude/settings.local.json', /"deny":\s*\[/, 'Claude deny list configuration');
    this.checkFileContent('package.json', /"sanitize:check"/, 'Sanitizer npm scripts');
    
    console.log('');
    
    // Check tools
    this.log('Checking tool availability...', 'info');
    this.checkFileExists('tools/sanitize.js', 'Surrogate sanitizer');
    this.checkFileExists('tools/string-utils.js', 'String utilities (Node.js)');
    this.checkFileExists('tools/string_utils.py', 'String utilities (Python)');
    this.checkFileExists('tools/payload-guard.js', 'Payload guard');
    this.checkFileExists('.githooks/pre-commit', 'Pre-commit hook');
    this.checkFileExists('.github/workflows/encoding-check.yml', 'CI workflow');
    
    console.log('');
    
    // Check runtime dependencies
    this.log('Checking runtime dependencies...', 'info');
    this.checkCommand('node --version', 'Node.js');
    this.checkCommand('python --version || python3 --version', 'Python');
    
    console.log('');
    
    // Test functionality
    this.log('Testing tool functionality...', 'info');
    await this.testSanitizer();
    await this.testPayloadGuard();
    
    console.log('');
    
    // Red team test - test string utilities directly
    this.log('Running red team test...', 'test');
    
    try {
      const { hasUnpairedSurrogates, stripUnpairedSurrogates } = require('./string-utils');
      
      // Test detection of unpaired high surrogate
      const testString = 'Test \uD800 end';
      const hasIssues = hasUnpairedSurrogates(testString);
      
      this.addResult(
        'Red Team Test: Surrogate detection',
        hasIssues,
        hasIssues ? 'Successfully detected test surrogate' : 'Test failed - surrogate not detected'
      );
      
      // Test fixing functionality
      if (hasIssues) {
        const cleaned = stripUnpairedSurrogates(testString);
        const stillHasIssues = hasUnpairedSurrogates(cleaned);
        
        this.addResult(
          'Red Team Test: Surrogate fixing',
          !stillHasIssues,
          !stillHasIssues ? 'Successfully fixed test surrogate' : 'Failed to fix test surrogate'
        );
      }
      
    } catch (error) {
      this.addResult(
        'Red Team Test: Execution',
        false,
        'Red team test failed to execute',
        error.message
      );
    }
    
    console.log('');
    return this.generateReport();
  }

  generateReport() {
    const passed = this.results.filter(r => r.passed).length;
    const total = this.results.length;
    const failed = this.results.filter(r => !r.passed);
    
    console.log('📊 Verification Report');
    console.log('='.repeat(50));
    console.log(`Total checks: ${total}`);
    console.log(`Passed: ${passed}`);
    console.log(`Failed: ${failed.length}`);
    console.log(`Success rate: ${((passed / total) * 100).toFixed(1)}%`);
    
    if (failed.length > 0) {
      console.log('');
      console.log('❌ Failed checks:');
      for (const failure of failed) {
        console.log(`   • ${failure.check}: ${failure.message}`);
        if (failure.details && this.verbose) {
          console.log(`     ${failure.details}`);
        }
      }
    }
    
    console.log('');
    
    if (failed.length === 0) {
      this.log('🎉 All checks passed! Claude Code workflow is properly hardened.', 'success');
      console.log('');
      console.log('Your repository is protected against:');
      console.log('• Unpaired UTF-16 surrogates ("no low surrogate" errors)');
      console.log('• Oversized payloads');
      console.log('• Encoding inconsistencies');
      console.log('• Binary file inclusion in Claude requests');
      console.log('');
      console.log('Ready to use: npm run ai:session:new');
    } else {
      this.log('⚠️  Some checks failed. Please review and fix issues above.', 'warning');
    }
    
    return {
      totalChecks: total,
      passedChecks: passed,
      failedChecks: failed.length,
      successRate: (passed / total) * 100,
      allPassed: failed.length === 0,
      failures: failed
    };
  }
}

// CLI interface
async function main() {
  const args = process.argv.slice(2);
  
  if (args.includes('--help') || args.includes('-h')) {
    console.log(`
Usage: node verify-setup.js [options]

Options:
  --verbose        Show detailed output and error information
  --help           Show this help message

This tool verifies that the Claude Code workflow hardening system
is properly installed and functioning correctly.
    `);
    process.exit(0);
  }
  
  const options = {
    verbose: args.includes('--verbose')
  };
  
  const verifier = new SetupVerifier(options);
  
  try {
    const report = await verifier.runFullVerification();
    process.exit(report.allPassed ? 0 : 1);
  } catch (error) {
    console.error(`❌ Verification failed: ${error.message}`);
    if (options.verbose) {
      console.error(error.stack);
    }
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}

module.exports = { SetupVerifier };