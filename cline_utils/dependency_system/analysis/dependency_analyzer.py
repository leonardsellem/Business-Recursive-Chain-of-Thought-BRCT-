"""
Analysis module for dependency detection and code analysis.
Parses files to identify imports, function calls, and other dependency indicators.
"""

import os
import ast
import re
import logging
from typing import Dict, List, Tuple, Set, Optional, Any
import importlib.util
import uuid

# Import only from utils, core, and io layers
from cline_utils.dependency_system.utils.path_utils import normalize_path, is_subpath
from cline_utils.dependency_system.utils.config_manager import ConfigManager
from cline_utils.dependency_system.utils.cache_manager import cached, invalidate_dependent_entries
from cline_utils.dependency_system.core.key_manager import get_key_from_path
from cline_utils.dependency_system.io.tracker_io import read_tracker_file

logger = logging.getLogger(__name__)

# Regular expressions for dependency detection
PYTHON_IMPORT_PATTERN = re.compile(
    r'(?:from\s+([.\w]+(?:\s*\.\s*[.\w]+)*)\s+import)|(?:import\s+([.\w]+(?:\s*,\s*[.\w]+)*))',
    re.MULTILINE
)
JAVASCRIPT_IMPORT_PATTERN = re.compile(
    r'(?:import\s+.*\s+from\s+["\']([^"\']+)["\'])|(?:require\s*\(\s*["\']([^"\']+)["\']\s*\))|(?:import\s*\(\s*["\']([^"\']+)["\']\s*\))'
)
MARKDOWN_LINK_PATTERN = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
HTML_LINK_PATTERN = re.compile(r'<a\s+(?:[^>]*?\s+)?href=(["\'])([^"\']+)\1')
CSS_IMPORT_PATTERN = re.compile(r'@import\s+(?:url\s*\(\s*)?["\']?([^"\')\s]+)["\']?(?:\s*\))?')

# @cached("file_type",
#        key_func=lambda file_path: f"file_type:{normalize_path(file_path)}:{os.path.getmtime(file_path) if os.path.exists(file_path) else 'missing'}:{os.path.getmtime(ConfigManager().config_path)}")
def get_file_type(file_path: str) -> str:
    """
    Determines the file type based on its extension.
    
    Args:
        file_path: The path to the file.
    Returns:
        The file type as a string (e.g., "py", "js", "md", "generic").
    """
    if not isinstance(file_path, str):
        logger.error(f"Invalid file_path type: {type(file_path)}")
        return "generic"
    _, ext = os.path.splitext(file_path)
    ext = ext.lower().lstrip('.')
    
    return {
        "py": "py",
        "js": "js", "ts": "js", "jsx": "js", "tsx": "js",
        "md": "md", "rst": "md",
        "html": "html", "htm": "html",
        "css": "css"
    }.get(ext, "generic")

@cached("file_analysis",
       key_func=lambda file_path: f"analyze_file:{normalize_path(file_path)}:{os.path.getmtime(file_path) if os.path.exists(file_path) else 'missing'}:{os.path.getmtime(ConfigManager().config_path)}")
def analyze_file(file_path: str) -> Dict[str, Any]:
    """
    Analyzes a file to identify dependencies, imports, and other metadata.
    
    Args:
        file_path: Path to the file to analyze
    Returns:
        Dictionary containing analysis results
    """
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        logger.warning(f"File not found or not a file: {file_path}")
        return {"error": "File not found or not a file"}

    # Exclude files based on configuration
    config_manager = ConfigManager()
    excluded_paths = config_manager.get_excluded_dirs()
    normalized_path = normalize_path(file_path)

    if any(normalized_path.startswith(normalize_path(excluded_path)) for excluded_path in excluded_paths):
        logger.info(f"Skipping analysis of excluded file: {file_path}")
        return {"skipped": "Excluded path"}

    try:
        file_type = get_file_type(file_path)
        
        analysis_result = {
            "file_path": file_path,
            "file_type": file_type,
            "imports": [],
            "functions": [],
            "classes": [],
            "references": [],
            "links": []
        }
        
        # Analyze based on file type
        if file_type == "py":
            _analyze_python_file(file_path, analysis_result)
        elif file_type == "js":
            _analyze_javascript_file(file_path, analysis_result)
        elif file_type == "md":
            _analyze_markdown_file(file_path, analysis_result)
        elif file_type == "html":
            _analyze_html_file(file_path, analysis_result)
        elif file_type == "css":
            _analyze_css_file(file_path, analysis_result)
        
        return analysis_result
    except FileNotFoundError:
        logger.warning(f"File not found during analysis: {file_path}")
        return {"error": "File not found"}
    except UnicodeDecodeError as e:
        logger.error(f"Encoding error in {file_path}: {str(e)}")
        return {"error": "Encoding error"}
    except Exception as e:
        logger.exception(f"Unexpected error analyzing {file_path}: {str(e)}")
        return {"error": str(e)}

def _analyze_python_file(file_path: str, result: Dict[str, Any]) -> None:
    """
    Analyzes a Python file for imports, functions, classes, and references.
    
    Args:
        file_path: Path to the Python file
        result: Dictionary to store analysis results (modified in-place)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract imports using regex
        import_matches = PYTHON_IMPORT_PATTERN.findall(content)
        result["imports"] = [match[0] or match[1] for match in import_matches if match[0] or match[1]]
        
        # Use AST for detailed analysis
        try:
            tree = ast.parse(content, filename=file_path)
            # Extract functions
            result["functions"] = [
                {"name": node.name, "args": [arg.arg for arg in node.args.args],
                 "line": node.lineno}
                for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
            ]
            # Extract classes
            result["classes"] = [
                {"name": node.name, "methods": [m.name for m in node.body if isinstance(m, ast.FunctionDef)],
                 "line": node.lineno}
                for node in ast.walk(tree) if isinstance(node, ast.ClassDef)
            ]
            # Extract references (variables, attributes)
            result["references"] = [
                {"name": node.id, "line": node.lineno}
                for node in ast.walk(tree) if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
            ]
        except SyntaxError:
            logger.warning(f"Syntax error in {file_path}, using regex only")
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
    except UnicodeDecodeError as e:
        logger.error(f"Encoding error in {file_path}: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error analyzing Python file {file_path}: {str(e)}")

def _analyze_javascript_file(file_path: str, result: Dict[str, Any]) -> None:
    """
    Analyzes a JavaScript file for imports and references.
    
    Args:
        file_path: Path to the JavaScript file
        result: Dictionary to store analysis results (modified in-place)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract imports
        import_matches = JAVASCRIPT_IMPORT_PATTERN.findall(content)
        result["imports"] = [match[0] or match[1] or match[2] for match in import_matches if any(match)]
        
        # Extract functions
        function_pattern = re.compile(r'(?:async\s+)?function\s+([a-zA-Z_$][\w$]*)\s*\(([^)]*)\)')
        function_matches = function_pattern.findall(content)
        result["functions"] = [
            {"name": name, "args": [arg.strip() for arg in args.split(',') if arg.strip()],
             "line": content[:content.find(f"function {name}")].count('\n') + 1}
            for name, args in function_matches
        ]
        
        # Extract arrow functions
        arrow_pattern = re.compile(r'(?:const|let|var)\s+([a-zA-Z_$][\w$]*)\s*=\s*(?:\(([^)]*)\)|([a-zA-Z_$][\w$]*))\s*=>')
        arrow_matches = arrow_pattern.findall(content)
        for name, args1, args2 in arrow_matches:
            args = args1 or args2
            result["functions"].append({
                "name": name,
                "args": [arg.strip() for arg in args.split(',') if arg.strip()],
                "line": content[:content.find(name)].count('\n') + 1,
                "type": "arrow"
            })
        
        # Extract classes
        class_pattern = re.compile(r'class\s+([a-zA-Z_$][\w$]*)')
        class_matches = class_pattern.findall(content)
        result["classes"] = [
            {"name": name, "line": content[:content.find(f"class {name}")].count('\n') + 1}
            for name in class_matches
        ]
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
    except UnicodeDecodeError as e:
        logger.error(f"Encoding error in {file_path}: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error analyzing JavaScript file {file_path}: {str(e)}")

def _analyze_markdown_file(file_path: str, result: Dict[str, Any]) -> None:
    """
    Analyzes a Markdown file for links and references.
    
    Args:
        file_path: Path to the Markdown file
        result: Dictionary to store analysis results (modified in-place)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract links
        link_matches = MARKDOWN_LINK_PATTERN.findall(content)
        result["links"] = [
            {"text": text, "url": url,
             "line": content[:content.find(f"[{text}]({url})")].count('\n') + 1}
            for text, url in link_matches
        ]
        
        # Extract code blocks
        code_block_pattern = re.compile(r'```(\w+)?\n(.*?)```', re.DOTALL)
        code_blocks = code_block_pattern.findall(content)
        result["code_blocks"] = [
            {"language": lang or "unspecified", "content": block.strip(),
             "line": content[:content.find(f"```{lang or ''}")].count('\n') + 1}
            for lang, block in code_blocks
        ]
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
    except UnicodeDecodeError as e:
        logger.error(f"Encoding error in {file_path}: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error analyzing Markdown file {file_path}: {str(e)}")

def _analyze_html_file(file_path: str, result: Dict[str, Any]) -> None:
    """
    Analyzes an HTML file for links, scripts, and stylesheet references.
    
    Args:
        file_path: Path to the HTML file
        result: Dictionary to store analysis results (modified in-place)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract links
        link_matches = HTML_LINK_PATTERN.findall(content)
        result["links"] = [
            {"url": url,
             "line": content[:content.find(f'href={quote}{url}{quote}')].count('\n') + 1 if content.find(f'href={quote}{url}{quote}') != -1 else 1}
            for quote, url in link_matches
        ]
        
        # Extract script tags
        script_pattern = re.compile(r'<script\s+(?:[^>]*?\s+)?src=(["\'])([^"\']+)\1')
        script_matches = script_pattern.findall(content)
        result["scripts"] = [
            {"src": src,
             "line": content[:content.find(f'src={quote}{src}{quote}')].count('\n') + 1 if content.find(f'src={quote}{src}{quote}') != -1 else 1}
            for quote, src in script_matches
        ]
        
        # Extract stylesheet links
        style_pattern = re.compile(r'<link\s+(?:[^>]*?\s+)?href=(["\'])([^"\']+)\1[^>]*?rel=(["\'])stylesheet\3')
        style_matches = style_pattern.findall(content)
        result["stylesheets"] = [
            {"href": href,
             "line": content[:content.find(f'href={quote1}{href}{quote1}')].count('\n') + 1 if content.find(f'href={quote1}{href}{quote1}') != -1 else 1}
            for quote1, href, quote2 in style_matches
        ]
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
    except UnicodeDecodeError as e:
        logger.error(f"Encoding error in {file_path}: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error analyzing HTML file {file_path}: {str(e)}")

def _analyze_css_file(file_path: str, result: Dict[str, Any]) -> None:
    """
    Analyzes a CSS file for imports and references.
    
    Args:
        file_path: Path to the CSS file
        result: Dictionary to store analysis results (modified in-place)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract imports
        import_matches = CSS_IMPORT_PATTERN.findall(content)
        result["imports"] = [
            {"url": url,
             "line": content[:content.find(url)].count('\n') + 1 if content.find(url) != -1 else 1}
            for url in import_matches
        ]
        
        # Extract selectors
        selector_pattern = re.compile(r'([.#][\w-]+)\s*\{')
        selector_matches = selector_pattern.findall(content)
        result["selectors"] = [
            {"selector": selector,
             "line": content[:content.find(f'{selector} {{')].count('\n') + 1 if content.find(f'{selector} {{') != -1 else 1}
            for selector in selector_matches
        ]
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
    except UnicodeDecodeError as e:
        logger.error(f"Encoding error in {file_path}: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error analyzing CSS file {file_path}: {str(e)}")


# End of file
