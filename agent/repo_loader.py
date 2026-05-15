"""
GitHub Repository Loader
Handles cloning, caching, and basic operations on repositories.
"""
import os
import shutil
import hashlib
from pathlib import Path
from typing import Optional, List
from git import Repo, GitCommandError
from django.conf import settings


class RepositoryLoader:
    """
    Manages GitHub repository cloning and caching.
    """
    
    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = storage_path or settings.REPO_STORAGE_PATH
        os.makedirs(self.storage_path, exist_ok=True)
    
    def _get_repo_hash(self, repo_url: str) -> str:
        """Generate a unique hash for a repository URL"""
        return hashlib.md5(repo_url.encode()).hexdigest()[:16]
    
    def _get_local_path(self, repo_url: str) -> str:
        """Get the local storage path for a repository"""
        repo_hash = self._get_repo_hash(repo_url)
        return os.path.join(self.storage_path, repo_hash)
    
    def get_or_clone(self, repo_url: str, force_refresh: bool = False) -> str:
        """
        Get local path to repository, cloning if necessary.
        
        Args:
            repo_url: GitHub repository URL
            force_refresh: If True, delete existing clone and re-clone
            
        Returns:
            Local path to the cloned repository
        """
        local_path = self._get_local_path(repo_url)
        
        # If force refresh, delete existing
        if force_refresh and os.path.exists(local_path):
            shutil.rmtree(local_path)
        
        # Clone if doesn't exist
        if not os.path.exists(local_path):
            return self._clone_repository(repo_url, local_path)
        
        # Update if exists
        return self._update_repository(local_path, repo_url)
    
    def _clone_repository(self, repo_url: str, local_path: str) -> str:
        """Clone a repository"""
        try:
            Repo.clone_from(repo_url, local_path, depth=1)
            return local_path
        except GitCommandError as e:
            raise Exception(f"Failed to clone repository {repo_url}: {str(e)}")
    
    def _update_repository(self, local_path: str, repo_url: str) -> str:
        """Update an existing repository"""
        try:
            repo = Repo(local_path)
            origin = repo.remotes.origin
            origin.pull()
            return local_path
        except GitCommandError:
            # If pull fails, re-clone
            shutil.rmtree(local_path)
            return self._clone_repository(repo_url, local_path)
    
    def list_files(
        self,
        local_path: str,
        relative_path: str = "",
        max_depth: int = 5,
        current_depth: int = 0
    ) -> List[str]:
        """
        List all files in repository (recursively with depth limit).
        
        Args:
            local_path: Root path of repository
            relative_path: Current relative path being explored
            max_depth: Maximum recursion depth
            current_depth: Current depth (internal)
            
        Returns:
            List of relative file paths
        """
        if current_depth >= max_depth:
            return []
        
        full_path = os.path.join(local_path, relative_path)
        if not os.path.exists(full_path):
            return []
        
        files = []
        ignored_dirs = settings.AGENT_IGNORED_DIRS
        ignored_exts = settings.AGENT_IGNORED_EXTENSIONS
        
        try:
            for item in os.listdir(full_path):
                # Skip hidden and ignored directories
                if item.startswith('.') or item in ignored_dirs:
                    continue
                
                item_path = os.path.join(relative_path, item)
                full_item_path = os.path.join(full_path, item)
                
                if os.path.isfile(full_item_path):
                    # Skip ignored extensions
                    if not any(item.endswith(ext) for ext in ignored_exts):
                        files.append(item_path)
                
                elif os.path.isdir(full_item_path):
                    # Recursively list subdirectory
                    files.extend(
                        self.list_files(
                            local_path,
                            item_path,
                            max_depth,
                            current_depth + 1
                        )
                    )
        except PermissionError:
            pass  # Skip directories we can't read
        
        return files
    
    def get_directory_structure(self, local_path: str, max_depth: int = 3) -> str:
        """
        Get a tree-like view of directory structure.
        
        Returns:
            String representation of directory tree
        """
        def build_tree(path: str, prefix: str = "", depth: int = 0) -> List[str]:
            if depth >= max_depth:
                return []
            
            lines = []
            ignored_dirs = settings.AGENT_IGNORED_DIRS
            
            try:
                items = sorted(os.listdir(path))
                items = [i for i in items if not i.startswith('.') and i not in ignored_dirs]
                
                for i, item in enumerate(items):
                    item_path = os.path.join(path, item)
                    is_last = i == len(items) - 1
                    
                    connector = "└── " if is_last else "├── "
                    lines.append(f"{prefix}{connector}{item}")
                    
                    if os.path.isdir(item_path):
                        extension = "    " if is_last else "│   "
                        lines.extend(
                            build_tree(item_path, prefix + extension, depth + 1)
                        )
            except PermissionError:
                pass
            
            return lines
        
        repo_name = os.path.basename(local_path)
        tree_lines = [repo_name] + build_tree(local_path)
        return "\n".join(tree_lines)
    
    def read_file(
        self,
        local_path: str,
        file_path: str,
        max_size: Optional[int] = None
    ) -> str:
        """
        Safely read a file from the repository.
        
        Args:
            local_path: Root path of repository
            file_path: Relative path to file
            max_size: Maximum file size in bytes (from settings if not provided)
            
        Returns:
            File content as string
        """
        max_size = max_size or settings.AGENT_MAX_FILE_SIZE
        
        # Prevent path traversal
        full_path = os.path.normpath(os.path.join(local_path, file_path))
        if not full_path.startswith(local_path):
            raise ValueError("Invalid file path (path traversal attempt)")
        
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Check file size
        file_size = os.path.getsize(full_path)
        if file_size > max_size:
            raise ValueError(f"File too large: {file_size} bytes (max: {max_size})")
        
        try:
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception as e:
            raise Exception(f"Failed to read file {file_path}: {str(e)}")
    
    def search_in_files(
        self,
        local_path: str,
        query: str,
        file_extensions: Optional[List[str]] = None,
        max_results: int = 20
    ) -> List[dict]:
        """
        Search for a text pattern in repository files.
        
        Args:
            local_path: Root path of repository
            query: Text to search for
            file_extensions: Optional list of extensions to search (e.g., ['.py', '.js'])
            max_results: Maximum number of results
            
        Returns:
            List of dicts with 'file', 'line_number', 'line_content'
        """
        results = []
        query_lower = query.lower()
        
        files = self.list_files(local_path)
        
        for file_path in files:
            # Filter by extension if specified
            if file_extensions:
                if not any(file_path.endswith(ext) for ext in file_extensions):
                    continue
            
            try:
                content = self.read_file(local_path, file_path)
                lines = content.split('\n')
                
                for line_num, line in enumerate(lines, 1):
                    if query_lower in line.lower():
                        results.append({
                            'file': file_path,
                            'line_number': line_num,
                            'line_content': line.strip()
                        })
                        
                        if len(results) >= max_results:
                            return results
            
            except Exception:
                continue  # Skip files that can't be read
        
        return results


# Singleton instance
_repo_loader = None

def get_repo_loader() -> RepositoryLoader:
    """Get or create repository loader singleton"""
    global _repo_loader
    if _repo_loader is None:
        _repo_loader = RepositoryLoader()
    return _repo_loader
