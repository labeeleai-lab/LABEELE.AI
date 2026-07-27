"""
Enhanced Configuration Module for DUKE System
Provides robust path management, environment-based configuration, and safe file operations
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timezone

# Initialize logger
logger = logging.getLogger(__name__)

# ==================== ENVIRONMENT DETECTION ====================

def get_environment() -> str:
    """Detect current environment (development, staging, production)"""
    return os.getenv("ENVIRONMENT", "development").lower()


def is_production() -> bool:
    """Check if running in production environment"""
    return get_environment() == "production"


# ==================== PATH CONFIGURATION ====================

class DukePathConfig:
    """
    Centralized path configuration for DUKE system
    Handles all file system paths with validation and creation
    """
    
    def __init__(self, base_dir: Optional[Path] = None):
        """
        Initialize path configuration
        
        Args:
            base_dir: Base directory for DUKE system. If None, uses current file location
        """
        # Base directory setup
        if base_dir is None:
            self.BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
        else:
            self.BASE_DIR = Path(base_dir)
        
        # Ensure base directory exists
        self.BASE_DIR.mkdir(exist_ok=True, parents=True)
        
        # Database configuration
        self._setup_database_paths()
        
        # Model checkpoint paths
        self._setup_checkpoint_paths()
        
        # Data and log paths
        self._setup_data_paths()
        
        # Service URLs
        self._setup_service_urls()
        
        # Create all necessary directories
        self._create_directories()
        
        logger.info(
            f"DUKE paths initialized",
            extra={
                "base_dir": str(self.BASE_DIR),
                "environment": get_environment()
            }
        )
    
    def _setup_database_paths(self):
        """Configure database paths based on environment"""
        env = get_environment()
        
        if env == "production":
            # Production uses PostgreSQL (configured via environment variable)
            self.DATABASE_URL = os.getenv(
                "DATABASE_URL",
                "postgresql://duke_user:changeme@localhost:5432/duke_production"
            )
            self.DB_PATH = None  # Not using file-based DB
            
            # Warn if still using default
            if "changeme" in self.DATABASE_URL:
                logger.warning(
                    "⚠️  Using default DATABASE_URL! Set proper credentials in environment."
                )
        
        elif env == "staging":
            # Staging can use PostgreSQL or SQLite
            self.DATABASE_URL = os.getenv(
                "DATABASE_URL",
                f"sqlite:///{self.BASE_DIR / 'duke_staging.db'}"
            )
            if "sqlite" in self.DATABASE_URL:
                self.DB_PATH = self.BASE_DIR / "duke_staging.db"
            else:
                self.DB_PATH = None
        
        else:  # development
            # Development uses SQLite by default
            db_name = os.getenv("DB_NAME", "duke_dev.db")
            self.DB_PATH = self.BASE_DIR / db_name
            self.DATABASE_URL = os.getenv(
                "DATABASE_URL",
                f"sqlite:///{self.DB_PATH}"
            )
        
        # Backup database path (for SQLite)
        if self.DB_PATH:
            self.DB_BACKUP_DIR = self.BASE_DIR / "backups" / "database"
        else:
            self.DB_BACKUP_DIR = self.BASE_DIR / "backups" / "exports"
    
    def _setup_checkpoint_paths(self):
        """Configure model checkpoint paths"""
        # Main checkpoint directory
        checkpoint_base = os.getenv("CHECKPOINT_DIR")
        if checkpoint_base:
            self.DUKE_CHECKPOINT_DIR = Path(checkpoint_base)
        else:
            self.DUKE_CHECKPOINT_DIR = self.BASE_DIR / "duke_checkpoints"
        
        # Model checkpoint files
        self.DUKE_MODEL_BEST = self.DUKE_CHECKPOINT_DIR / "duke_model_best.pth"
        self.DUKE_MODEL_LAST = self.DUKE_CHECKPOINT_DIR / "duke_model_latest.pth"
        self.DUKE_MODEL_BACKUP = self.DUKE_CHECKPOINT_DIR / "duke_model_backup.pth"
        
        # Embedder and response database
        self.DUKE_EMBEDDER = self.DUKE_CHECKPOINT_DIR / "duke_embedder.pkl"
        self.DUKE_RESPONSES = self.DUKE_CHECKPOINT_DIR / "duke_responses.pkl"
        
        # Versioned checkpoints directory
        self.CHECKPOINT_VERSIONS_DIR = self.DUKE_CHECKPOINT_DIR / "versions"
        
        # Training artifacts
        self.TRAINING_ARTIFACTS_DIR = self.DUKE_CHECKPOINT_DIR / "training_artifacts"
    
    def _setup_data_paths(self):
        """Configure data and log paths"""
        # Assets directory
        self.ASSETS_DIR = self.BASE_DIR / "assets"
        
        # Data directory
        self.DATA_DIR = self.BASE_DIR / "data"
        
        # Logs directory
        self.LOGS_DIR = self.DATA_DIR / "logs"
        
        # Memory and training files
        self.MEMORY_FILE = self.DATA_DIR / "duke_training_memory.json"
        self.FEEDBACK_LOG_FILE = self.DATA_DIR / "feedback_log.jsonl"
        self.TRAINING_LOG_FILE = self.DATA_DIR / "training_log.json"
        
        # System log
        self.SYSTEM_LOG_FILE = self.LOGS_DIR / "duke_system.log"
        self.ERROR_LOG_FILE = self.LOGS_DIR / "duke_errors.log"
        
        # Temporary files
        self.TEMP_DIR = self.BASE_DIR / "temp"
        
        # Export directory
        self.EXPORT_DIR = self.BASE_DIR / "exports"
    
    def _setup_service_urls(self):
        """Configure service URLs"""
        self.VISION_NODE_URL = os.getenv(
            "VISION_NODE_URL", 
            "http://localhost:8003"
        )
        
        self.API_BASE_URL = os.getenv(
            "API_BASE_URL",
            "http://localhost:8000"
        )
        
        # Redis URL for caching
        self.REDIS_URL = os.getenv(
            "REDIS_URL",
            "redis://localhost:6379/0"
        )
    
    def _create_directories(self):
        """Create all necessary directories"""
        directories = [
            self.DUKE_CHECKPOINT_DIR,
            self.CHECKPOINT_VERSIONS_DIR,
            self.TRAINING_ARTIFACTS_DIR,
            self.ASSETS_DIR,
            self.DATA_DIR,
            self.LOGS_DIR,
            self.TEMP_DIR,
            self.EXPORT_DIR,
            self.DB_BACKUP_DIR,
        ]
        
        for directory in directories:
            try:
                directory.mkdir(exist_ok=True, parents=True)
                logger.debug(f"Ensured directory exists: {directory}")
            except Exception as e:
                logger.error(f"Failed to create directory {directory}: {e}")
                raise
    
    def get_checkpoint_path(self, version: Optional[str] = None) -> Path:
        """
        Get checkpoint path, optionally for a specific version
        
        Args:
            version: Model version (e.g., "v1.0.0", "20240101_120000")
        
        Returns:
            Path to checkpoint file
        """
        if version:
            versioned_path = self.CHECKPOINT_VERSIONS_DIR / f"duke_model_{version}.pth"
            return versioned_path
        return self.DUKE_MODEL_LAST
    
    def get_backup_path(self, filename: str) -> Path:
        """
        Get timestamped backup path for a file
        
        Args:
            filename: Base filename for backup
        
        Returns:
            Path with timestamp
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_name = f"{Path(filename).stem}_{timestamp}{Path(filename).suffix}"
        return self.DB_BACKUP_DIR / backup_name
    
    def cleanup_temp_files(self, max_age_hours: int = 24):
        """
        Clean up temporary files older than specified age
        
        Args:
            max_age_hours: Maximum age in hours before deletion
        """
        import time
        
        if not self.TEMP_DIR.exists():
            return
        
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        deleted_count = 0
        for temp_file in self.TEMP_DIR.iterdir():
            if temp_file.is_file():
                file_age = current_time - temp_file.stat().st_mtime
                if file_age > max_age_seconds:
                    try:
                        temp_file.unlink()
                        deleted_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to delete temp file {temp_file}: {e}")
        
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} temporary files")
    
    def validate_paths(self) -> Dict[str, bool]:
        """
        Validate that all critical paths are accessible
        
        Returns:
            Dictionary of path validation results
        """
        validation_results = {}
        
        critical_dirs = {
            'base_dir': self.BASE_DIR,
            'checkpoint_dir': self.DUKE_CHECKPOINT_DIR,
            'data_dir': self.DATA_DIR,
            'logs_dir': self.LOGS_DIR,
        }
        
        for name, path in critical_dirs.items():
            try:
                # Check if directory exists and is writable
                test_file = path / '.write_test'
                test_file.touch()
                test_file.unlink()
                validation_results[name] = True
            except Exception as e:
                logger.error(f"Path validation failed for {name} ({path}): {e}")
                validation_results[name] = False
        
        return validation_results
    
    def to_dict(self) -> Dict[str, Any]:
        """Export configuration as dictionary"""
        return {
            'base_dir': str(self.BASE_DIR),
            'database_url': self.DATABASE_URL,
            'checkpoint_dir': str(self.DUKE_CHECKPOINT_DIR),
            'data_dir': str(self.DATA_DIR),
            'logs_dir': str(self.LOGS_DIR),
            'environment': get_environment(),
        }


# ==================== SAFE FILE OPERATIONS ====================

class SafeFileManager:
    """
    Provides safe file operations with error handling and validation
    """
    
    @staticmethod
    def ensure_file_exists(filepath: Path, default_content: Any = None):
        """
        Ensure a file exists, create with default content if not
        
        Args:
            filepath: Path to file
            default_content: Default content to write (will be JSON-serialized if dict/list)
        """
        if not filepath.exists():
            try:
                filepath.parent.mkdir(exist_ok=True, parents=True)
                
                if default_content is not None:
                    if isinstance(default_content, (dict, list)):
                        # JSON content
                        with open(filepath, 'w') as f:
                            json.dump(default_content, f, indent=2)
                    else:
                        # Text content
                        with open(filepath, 'w') as f:
                            f.write(str(default_content))
                else:
                    # Create empty file
                    filepath.touch()
                
                logger.info(f"Created file: {filepath}")
            except Exception as e:
                logger.error(f"Failed to create file {filepath}: {e}")
                raise
    
    @staticmethod
    def safe_json_load(filepath: Path, default: Any = None) -> Any:
        """
        Safely load JSON file with fallback
        
        Args:
            filepath: Path to JSON file
            default: Default value if file doesn't exist or is invalid
        
        Returns:
            Loaded JSON data or default value
        """
        try:
            if not filepath.exists():
                logger.warning(f"JSON file not found: {filepath}, using default")
                return default if default is not None else {}
            
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            return data
        
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {filepath}: {e}, using default")
            return default if default is not None else {}
        
        except Exception as e:
            logger.error(f"Error loading JSON from {filepath}: {e}")
            return default if default is not None else {}
    
    @staticmethod
    def safe_json_save(filepath: Path, data: Any, create_backup: bool = True) -> bool:
        """
        Safely save JSON file with optional backup
        
        Args:
            filepath: Path to JSON file
            data: Data to save
            create_backup: Whether to create backup of existing file
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create backup if file exists
            if create_backup and filepath.exists():
                backup_path = filepath.with_suffix('.json.bak')
                try:
                    import shutil
                    shutil.copy2(filepath, backup_path)
                except Exception as e:
                    logger.warning(f"Failed to create backup: {e}")
            
            # Ensure parent directory exists
            filepath.parent.mkdir(exist_ok=True, parents=True)
            
            # Write to temporary file first
            temp_path = filepath.with_suffix('.json.tmp')
            with open(temp_path, 'w') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Atomic rename
            temp_path.replace(filepath)
            
            logger.debug(f"Saved JSON to {filepath}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to save JSON to {filepath}: {e}")
            return False
    
    @staticmethod
    def append_jsonl(filepath: Path, data: Dict) -> bool:
        """
        Append JSON line to JSONL file
        
        Args:
            filepath: Path to JSONL file
            data: Dictionary to append as JSON line
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure parent directory exists
            filepath.parent.mkdir(exist_ok=True, parents=True)
            
            # Append with timestamp
            data['_timestamp'] = datetime.now(timezone.utc).isoformat()
            
            with open(filepath, 'a') as f:
                json.dump(data, f, ensure_ascii=False)
                f.write('\n')
            
            return True
        
        except Exception as e:
            logger.error(f"Failed to append to JSONL {filepath}: {e}")
            return False
    
    @staticmethod
    def read_jsonl(filepath: Path, max_lines: Optional[int] = None) -> list:
        """
        Read JSONL file into list of dictionaries
        
        Args:
            filepath: Path to JSONL file
            max_lines: Maximum number of lines to read (None for all)
        
        Returns:
            List of dictionaries
        """
        if not filepath.exists():
            return []
        
        results = []
        try:
            with open(filepath, 'r') as f:
                for i, line in enumerate(f):
                    if max_lines and i >= max_lines:
                        break
                    
                    try:
                        data = json.loads(line.strip())
                        results.append(data)
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON line {i} in {filepath}")
                        continue
            
            return results
        
        except Exception as e:
            logger.error(f"Error reading JSONL from {filepath}: {e}")
            return []


# ==================== TRAINING LOGGER INTEGRATION ====================

class TrainingLoggerManager:
    """
    Manages training logger with safe fallbacks
    """
    
    def __init__(self, paths: DukePathConfig):
        self.paths = paths
        self.logger_available = False
        
        # Try to import training logger
        try:
            from openai_training_logger import (
                log_openai_call,
                get_training_stats,
                load_training_data_for_duke,
                get_api_key_status,
                TRAINING_LOG_FILE
            )
            
            self.log_openai_call = log_openai_call
            self.get_training_stats = get_training_stats
            self.load_training_data_for_duke = load_training_data_for_duke
            self.get_api_key_status = get_api_key_status
            self.TRAINING_LOG_FILE = TRAINING_LOG_FILE
            
            self.logger_available = True
            logger.info("✅ Training logger loaded successfully")
        
        except ImportError as e:
            logger.warning(f"⚠️  Training logger not found: {e}, using fallbacks")
            self._setup_fallbacks()
    
    def _setup_fallbacks(self):
        """Setup fallback functions when training logger is not available"""
        
        self.TRAINING_LOG_FILE = str(self.paths.TRAINING_LOG_FILE)
        
        # Ensure training log file exists
        SafeFileManager.ensure_file_exists(
            self.paths.TRAINING_LOG_FILE,
            default_content={"calls": [], "stats": {}}
        )
        
        def log_openai_call(*args, **kwargs):
            """Fallback: log to local file"""
            try:
                call_data = {
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'args': str(args),
                    'kwargs': str(kwargs),
                }
                SafeFileManager.append_jsonl(
                    self.paths.TRAINING_LOG_FILE.with_suffix('.jsonl'),
                    call_data
                )
            except Exception as e:
                logger.error(f"Failed to log OpenAI call: {e}")
        
        def get_training_stats() -> Dict:
            """Fallback: return basic stats"""
            return {
                'total_calls': 0,
                'estimated_cost_usd': 0.0,
                'training_samples_available': 0,
                'status': 'fallback_mode'
            }
        
        def load_training_data_for_duke(*args, **kwargs) -> list:
            """Fallback: return empty list"""
            return []
        
        def get_api_key_status() -> Dict:
            """Fallback: check environment"""
            api_key = os.getenv("OPENAI_API_KEY")
            return {
                'configured': bool(api_key),
                'key_prefix': api_key[:20] if api_key else None,
                'status': 'configured' if api_key else 'not_configured'
            }
        
        self.log_openai_call = log_openai_call
        self.get_training_stats = get_training_stats
        self.load_training_data_for_duke = load_training_data_for_duke
        self.get_api_key_status = get_api_key_status


# ==================== INITIALIZATION ====================

def initialize_duke_config(base_dir: Optional[Path] = None) -> tuple[DukePathConfig, TrainingLoggerManager]:
    """
    Initialize DUKE configuration system
    
    Args:
        base_dir: Optional base directory override
    
    Returns:
        Tuple of (DukePathConfig, TrainingLoggerManager)
    """
    # Initialize paths
    paths = DukePathConfig(base_dir)
    
    # Initialize training logger
    training_logger = TrainingLoggerManager(paths)
    
    # Initialize critical files
    SafeFileManager.ensure_file_exists(
        paths.MEMORY_FILE,
        default_content=[]
    )
    
    SafeFileManager.ensure_file_exists(
        paths.FEEDBACK_LOG_FILE,
        default_content=""
    )
    
    # Validate paths
    validation = paths.validate_paths()
    if not all(validation.values()):
        failed_paths = [k for k, v in validation.items() if not v]
        logger.error(f"Path validation failed for: {failed_paths}")
        raise RuntimeError(f"Critical paths not accessible: {failed_paths}")
    
    # Log configuration summary
    logger.info(
        "DUKE configuration initialized",
        extra={
            "environment": get_environment(),
            "database": "PostgreSQL" if "postgresql" in paths.DATABASE_URL else "SQLite",
            "training_logger": "available" if training_logger.logger_available else "fallback",
        }
    )
    
    return paths, training_logger


# ==================== USAGE EXAMPLE ====================

if __name__ == "__main__":
    """
    Example usage and testing
    """
    # Set up basic logging for demo
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 70)
    print("DUKE Configuration System - Test")
    print("=" * 70)
    
    # Initialize configuration
    paths, training_mgr = initialize_duke_config()
    
    # Display configuration
    print("\n📂 Path Configuration:")
    for key, value in paths.to_dict().items():
        print(f"  {key}: {value}")
    
    # Test file operations
    print("\n🧪 Testing file operations...")
    
    test_data = {"test": "data", "timestamp": datetime.now(timezone.utc).isoformat()}
    test_file = paths.TEMP_DIR / "test.json"
    
    if SafeFileManager.safe_json_save(test_file, test_data):
        print("  ✅ JSON save successful")
    
    loaded_data = SafeFileManager.safe_json_load(test_file)
    if loaded_data == test_data:
        print("  ✅ JSON load successful")
    
    # Test JSONL operations
    jsonl_file = paths.TEMP_DIR / "test.jsonl"
    for i in range(3):
        SafeFileManager.append_jsonl(jsonl_file, {"entry": i})
    
    jsonl_data = SafeFileManager.read_jsonl(jsonl_file)
    print(f"  ✅ JSONL operations successful ({len(jsonl_data)} entries)")
    
    # Cleanup
    paths.cleanup_temp_files(max_age_hours=0)
    print("  ✅ Temp file cleanup successful")
    
    # Validate paths
    print("\n🔍 Path validation:")
    validation = paths.validate_paths()
    for path_name, is_valid in validation.items():
        status = "✅" if is_valid else "❌"
        print(f"  {status} {path_name}")
    
    print("\n✅ All tests passed!")
