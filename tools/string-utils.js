/**
 * Safe String Utilities for UTF-8 Processing
 * 
 * Provides utilities to detect and sanitize unpaired UTF-16 surrogate
 * characters that can cause "no low surrogate" errors in Claude Code.
 */

const UNICODE_REPLACEMENT_CHAR = '\uFFFD';

/**
 * Check if a string contains unpaired UTF-16 surrogate characters
 * @param {string} str - The string to check
 * @returns {boolean} True if string contains unpaired surrogates
 */
function hasUnpairedSurrogates(str) {
  if (typeof str !== 'string') return false;
  
  for (let i = 0; i < str.length; i++) {
    const code = str.charCodeAt(i);
    
    // High surrogate (U+D800-U+DBFF)
    if (code >= 0xD800 && code <= 0xDBFF) {
      const nextCode = i + 1 < str.length ? str.charCodeAt(i + 1) : -1;
      
      // Not followed by low surrogate
      if (nextCode < 0xDC00 || nextCode > 0xDFFF) {
        return true;
      }
      
      // Skip the low surrogate in next iteration
      i++;
    }
    // Low surrogate (U+DC00-U+DFFF) without preceding high surrogate
    else if (code >= 0xDC00 && code <= 0xDFFF) {
      return true;
    }
  }
  
  return false;
}

/**
 * Check if a string is safe for UTF-8 transport (no unpaired surrogates)
 * @param {string} str - The string to check
 * @returns {boolean} True if string is UTF-8 safe
 */
function isUtf8Safe(str) {
  return !hasUnpairedSurrogates(str);
}

/**
 * Strip unpaired surrogate characters from a string
 * @param {string} str - The string to sanitize
 * @param {string} replacement - Character to replace surrogates with (default: Unicode replacement character)
 * @returns {string} Sanitized string
 */
function stripUnpairedSurrogates(str, replacement = UNICODE_REPLACEMENT_CHAR) {
  if (typeof str !== 'string') return str;
  if (!hasUnpairedSurrogates(str)) return str;
  
  let result = '';
  
  for (let i = 0; i < str.length; i++) {
    const char = str[i];
    const code = char.charCodeAt(0);
    
    // High surrogate
    if (code >= 0xD800 && code <= 0xDBFF) {
      const nextChar = str[i + 1];
      const nextCode = nextChar ? nextChar.charCodeAt(0) : -1;
      
      // Followed by low surrogate - keep both
      if (nextCode >= 0xDC00 && nextCode <= 0xDFFF) {
        result += char + nextChar;
        i++; // Skip the low surrogate
      }
      // Unpaired high surrogate - replace
      else {
        result += replacement;
      }
    }
    // Low surrogate without preceding high surrogate - replace
    else if (code >= 0xDC00 && code <= 0xDFFF) {
      result += replacement;
    }
    // Normal character
    else {
      result += char;
    }
  }
  
  return result;
}

/**
 * Get detailed information about surrogate issues in a string
 * @param {string} str - The string to analyze
 * @returns {Array} Array of surrogate issue objects
 */
function analyzeSurrogates(str) {
  if (typeof str !== 'string') return [];
  
  const issues = [];
  
  for (let i = 0; i < str.length; i++) {
    const char = str[i];
    const code = char.charCodeAt(0);
    
    // High surrogate
    if (code >= 0xD800 && code <= 0xDBFF) {
      const nextChar = str[i + 1];
      const nextCode = nextChar ? nextChar.charCodeAt(0) : -1;
      
      // Not followed by low surrogate
      if (nextCode < 0xDC00 || nextCode > 0xDFFF) {
        issues.push({
          type: 'unpaired_high_surrogate',
          position: i,
          char: char,
          code: `U+${code.toString(16).toUpperCase().padStart(4, '0')}`,
          description: 'High surrogate not followed by low surrogate'
        });
      } else {
        // Skip the valid pair
        i++;
      }
    }
    // Low surrogate without preceding high surrogate
    else if (code >= 0xDC00 && code <= 0xDFFF) {
      issues.push({
        type: 'unpaired_low_surrogate',
        position: i,
        char: char,
        code: `U+${code.toString(16).toUpperCase().padStart(4, '0')}`,
        description: 'Low surrogate without preceding high surrogate'
      });
    }
  }
  
  return issues;
}

/**
 * Safely truncate a string while preserving UTF-16 surrogate pairs
 * @param {string} str - The string to truncate
 * @param {number} maxLength - Maximum length in characters
 * @param {string} ellipsis - String to append if truncated
 * @returns {string} Truncated string
 */
function safeTruncate(str, maxLength, ellipsis = '...') {
  if (typeof str !== 'string' || str.length <= maxLength) return str;
  
  let truncated = str.slice(0, maxLength - ellipsis.length);
  
  // Check if we truncated in the middle of a surrogate pair
  if (truncated.length > 0) {
    const lastCode = truncated.charCodeAt(truncated.length - 1);
    
    // If last character is a high surrogate, remove it to avoid unpaired surrogate
    if (lastCode >= 0xD800 && lastCode <= 0xDBFF) {
      truncated = truncated.slice(0, -1);
    }
  }
  
  return truncated + ellipsis;
}

/**
 * Calculate the byte size of a string when encoded as UTF-8
 * @param {string} str - The string to measure
 * @returns {number} Size in bytes
 */
function getUtf8ByteLength(str) {
  if (typeof str !== 'string') return 0;
  
  // Use TextEncoder for accurate UTF-8 byte length
  return new TextEncoder().encode(str).length;
}

/**
 * Check if a string would exceed a size limit when encoded as UTF-8
 * @param {string} str - The string to check
 * @param {number} maxBytes - Maximum size in bytes
 * @returns {boolean} True if string exceeds limit
 */
function exceedsUtf8Limit(str, maxBytes) {
  return getUtf8ByteLength(str) > maxBytes;
}

/**
 * Sanitize multiple strings for safe UTF-8 transport
 * @param {Array<string>} strings - Array of strings to sanitize
 * @param {string} replacement - Replacement character for surrogates
 * @returns {Array<string>} Array of sanitized strings
 */
function sanitizeStrings(strings, replacement = UNICODE_REPLACEMENT_CHAR) {
  return strings.map(str => stripUnpairedSurrogates(str, replacement));
}

// Export all utilities
module.exports = {
  hasUnpairedSurrogates,
  isUtf8Safe,
  stripUnpairedSurrogates,
  analyzeSurrogates,
  safeTruncate,
  getUtf8ByteLength,
  exceedsUtf8Limit,
  sanitizeStrings,
  UNICODE_REPLACEMENT_CHAR
};

// For ES modules
if (typeof exports === 'undefined') {
  this.StringUtils = module.exports;
}