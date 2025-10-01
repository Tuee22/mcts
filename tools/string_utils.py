"""
Safe String Utilities for UTF-8 Processing

Provides utilities to detect and sanitize unpaired UTF-16 surrogate
characters that can cause "no low surrogate" errors in Claude Code.
"""

import re
from typing import List, Dict, Union, Optional, TypedDict

UNICODE_REPLACEMENT_CHAR = "\uFFFD"


def has_unpaired_surrogates(text: str) -> bool:
    """
    Check if a string contains unpaired UTF-16 surrogate characters.

    Args:
        text: The string to check

    Returns:
        True if string contains unpaired surrogates
    """

    i = 0
    while i < len(text):
        char = text[i]
        code = ord(char)

        # High surrogate (U+D800-U+DBFF)
        if 0xD800 <= code <= 0xDBFF:
            if i + 1 < len(text):
                next_code = ord(text[i + 1])
                # Not followed by low surrogate
                if not (0xDC00 <= next_code <= 0xDFFF):
                    return True
                # Valid pair, skip both
                i += 2
            else:
                # High surrogate at end of string
                return True
        # Low surrogate (U+DC00-U+DFFF) without preceding high surrogate
        elif 0xDC00 <= code <= 0xDFFF:
            return True
        else:
            i += 1

    return False


def is_utf8_safe(text: str) -> bool:
    """
    Check if a string is safe for UTF-8 transport (no unpaired surrogates).

    Args:
        text: The string to check

    Returns:
        True if string is UTF-8 safe
    """
    return not has_unpaired_surrogates(text)


def strip_unpaired_surrogates(
    text: str, replacement: str = UNICODE_REPLACEMENT_CHAR
) -> str:
    """
    Strip unpaired surrogate characters from a string.

    Args:
        text: The string to sanitize
        replacement: Character to replace surrogates with

    Returns:
        Sanitized string
    """

    if not has_unpaired_surrogates(text):
        return text

    result = []
    i = 0

    while i < len(text):
        char = text[i]
        code = ord(char)

        # High surrogate
        if 0xD800 <= code <= 0xDBFF:
            if i + 1 < len(text):
                next_char = text[i + 1]
                next_code = ord(next_char)

                # Followed by low surrogate - keep both
                if 0xDC00 <= next_code <= 0xDFFF:
                    result.append(char)
                    result.append(next_char)
                    i += 2
                    continue

            # Unpaired high surrogate - replace
            result.append(replacement)
            i += 1

        # Low surrogate without preceding high surrogate - replace
        elif 0xDC00 <= code <= 0xDFFF:
            result.append(replacement)
            i += 1

        # Normal character
        else:
            result.append(char)
            i += 1

    return "".join(result)


class SurrogateIssue(TypedDict):
    type: str
    position: int
    char: str
    code: str
    description: str


def analyze_surrogates(text: str) -> List[SurrogateIssue]:
    """
    Get detailed information about surrogate issues in a string.

    Args:
        text: The string to analyze

    Returns:
        List of surrogate issue dictionaries
    """

    issues = []
    i = 0

    while i < len(text):
        char = text[i]
        code = ord(char)

        # High surrogate
        if 0xD800 <= code <= 0xDBFF:
            if i + 1 < len(text):
                next_code = ord(text[i + 1])
                # Not followed by low surrogate
                if not (0xDC00 <= next_code <= 0xDFFF):
                    issues.append(
                        SurrogateIssue(
                            type="unpaired_high_surrogate",
                            position=i,
                            char=char,
                            code=f"U+{code:04X}",
                            description="High surrogate not followed by low surrogate",
                        )
                    )
                else:
                    # Skip the valid pair
                    i += 1
            else:
                # High surrogate at end of string
                issues.append(
                    SurrogateIssue(
                        type="unpaired_high_surrogate",
                        position=i,
                        char=char,
                        code=f"U+{code:04X}",
                        description="High surrogate at end of string",
                    )
                )

        # Low surrogate without preceding high surrogate
        elif 0xDC00 <= code <= 0xDFFF:
            issues.append(
                SurrogateIssue(
                    type="unpaired_low_surrogate",
                    position=i,
                    char=char,
                    code=f"U+{code:04X}",
                    description="Low surrogate without preceding high surrogate",
                )
            )

        i += 1

    return issues


def safe_truncate(text: str, max_length: int, ellipsis: str = "...") -> str:
    """
    Safely truncate a string while preserving UTF-16 surrogate pairs.

    Args:
        text: The string to truncate
        max_length: Maximum length in characters
        ellipsis: String to append if truncated

    Returns:
        Truncated string
    """
    if not isinstance(text, str) or len(text) <= max_length:
        return text

    truncated = text[: max_length - len(ellipsis)]

    # Check if we truncated in the middle of a surrogate pair
    if truncated:
        last_code = ord(truncated[-1])

        # If last character is a high surrogate, remove it to avoid unpaired surrogate
        if 0xD800 <= last_code <= 0xDBFF:
            truncated = truncated[:-1]

    return truncated + ellipsis


def get_utf8_byte_length(text: str) -> int:
    """
    Calculate the byte size of a string when encoded as UTF-8.

    Args:
        text: The string to measure

    Returns:
        Size in bytes
    """

    return len(text.encode("utf-8"))


def exceeds_utf8_limit(text: str, max_bytes: int) -> bool:
    """
    Check if a string would exceed a size limit when encoded as UTF-8.

    Args:
        text: The string to check
        max_bytes: Maximum size in bytes

    Returns:
        True if string exceeds limit
    """
    return get_utf8_byte_length(text) > max_bytes


def sanitize_strings(
    strings: List[str], replacement: str = UNICODE_REPLACEMENT_CHAR
) -> List[str]:
    """
    Sanitize multiple strings for safe UTF-8 transport.

    Args:
        strings: List of strings to sanitize
        replacement: Replacement character for surrogates

    Returns:
        List of sanitized strings
    """
    return [strip_unpaired_surrogates(s, replacement) for s in strings]


class EncodingIssueResult(TypedDict, total=False):
    file: str
    encoding: str
    readable: bool
    surrogate_issues: List[SurrogateIssue]
    has_issues: bool
    byte_size: int
    char_count: int
    error: str


def detect_encoding_issues(file_path: str) -> EncodingIssueResult:
    """
    Detect encoding issues in a file.

    Args:
        file_path: Path to the file to check

    Returns:
        Dictionary with encoding issue information
    """
    try:
        # Try to read as UTF-8
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        issues = analyze_surrogates(content)

        return EncodingIssueResult(
            file=file_path,
            encoding="utf-8",
            readable=True,
            surrogate_issues=issues,
            has_issues=len(issues) > 0,
            byte_size=get_utf8_byte_length(content),
            char_count=len(content),
        )

    except UnicodeDecodeError as e:
        return EncodingIssueResult(
            file=file_path,
            encoding="unknown",
            readable=False,
            error=str(e),
            surrogate_issues=[],
            has_issues=True,
        )
    except Exception as e:
        return EncodingIssueResult(
            file=file_path,
            encoding="unknown",
            readable=False,
            error=str(e),
            surrogate_issues=[],
            has_issues=True,
        )


class FixResult(TypedDict, total=False):
    file: str
    fixed: bool
    issues_found: int
    issues: List[SurrogateIssue]
    backup_created: bool
    message: str
    error: str


def fix_file_surrogates(
    file_path: str, backup: bool = True, replacement: str = UNICODE_REPLACEMENT_CHAR
) -> FixResult:
    """
    Fix surrogate issues in a file.

    Args:
        file_path: Path to the file to fix
        backup: Whether to create a backup file
        replacement: Character to replace surrogates with

    Returns:
        Dictionary with fix results
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            original_content = f.read()

        if not has_unpaired_surrogates(original_content):
            return FixResult(
                file=file_path,
                fixed=False,
                issues_found=0,
                message="No surrogate issues found",
            )

        # Create backup if requested
        if backup:
            backup_path = file_path + ".sanitize-backup"
            with open(backup_path, "w", encoding="utf-8") as f:
                f.write(original_content)

        # Fix the content
        issues = analyze_surrogates(original_content)
        fixed_content = strip_unpaired_surrogates(original_content, replacement)

        # Write the fixed content
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(fixed_content)

        return FixResult(
            file=file_path,
            fixed=True,
            issues_found=len(issues),
            issues=issues,
            backup_created=backup,
            message=f"Fixed {len(issues)} surrogate issue(s)",
        )

    except Exception as e:
        return FixResult(
            file=file_path,
            fixed=False,
            issues_found=0,
            error=str(e),
            message=f"Error fixing file: {e}",
        )


# Command-line interface
if __name__ == "__main__":
    import sys
    import os

    def print_usage() -> None:
        print(
            """
Usage: python string_utils.py [command] [args]

Commands:
  check <file>     - Check file for surrogate issues
  fix <file>       - Fix surrogate issues in file
  analyze <text>   - Analyze text for surrogate issues
  
Examples:
  python string_utils.py check myfile.txt
  python string_utils.py fix myfile.txt
  python string_utils.py analyze "Hello \uD800 World"
        """
        )

    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    command = sys.argv[1]

    if command == "check" and len(sys.argv) >= 3:
        file_path = sys.argv[2]
        result = detect_encoding_issues(file_path)

        if result["has_issues"]:
            print(f"❌ Issues found in {file_path}:")
            if "surrogate_issues" in result:
                for issue in result["surrogate_issues"]:
                    print(
                        f"  {issue['type']} at position {issue['position']}: {issue['description']}"
                    )
            sys.exit(1)
        else:
            print(f"✅ No issues found in {file_path}")

    elif command == "fix" and len(sys.argv) >= 3:
        file_path = sys.argv[2]
        fix_result = fix_file_surrogates(file_path)

        if fix_result["fixed"]:
            print(f"🔧 {fix_result['message']} in {file_path}")
        else:
            print(f"ℹ️  {fix_result['message']} in {file_path}")

    elif command == "analyze" and len(sys.argv) >= 3:
        text = sys.argv[2]
        issues = analyze_surrogates(text)

        if issues:
            print(f"❌ Found {len(issues)} surrogate issue(s):")
            for issue in issues:
                print(
                    f"  {issue['type']} at position {issue['position']}: {issue['description']}"
                )
        else:
            print("✅ No surrogate issues found")

    else:
        print_usage()
        sys.exit(1)
