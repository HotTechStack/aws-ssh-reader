#!/usr/bin/env python3
"""
AWS SSH Directory Access Script
Connects to AWS instance and performs directory operations
"""

import paramiko
import os
import sys
import argparse
from pathlib import Path
import logging
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class AWSSSHClient:
    def __init__(self, hostname: str, username: str, key_path: str, port: int = 22):
        """
        Initialize SSH client for AWS connection

        Args:
            hostname: AWS instance IP or hostname
            username: SSH username
            key_path: Path to SSH private key
            port: SSH port (default 22)
        """
        self.hostname = hostname
        self.username = username
        self.key_path = Path(key_path).expanduser()
        self.port = port
        self.client = None
        self.sftp = None

    def __enter__(self):
        """Context manager entry"""
        if self.connect():
            return self
        else:
            raise Exception("Failed to establish SSH connection")

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()

    def connect(self) -> bool:
        """
        Establish SSH connection to AWS instance

        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            # Create SSH client
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            # Load private key
            if not self.key_path.exists():
                logger.error(f"SSH key not found: {self.key_path}")
                return False

            private_key = paramiko.RSAKey.from_private_key_file(str(self.key_path))

            # Connect
            logger.info(f"Connecting to {self.hostname}...")
            self.client.connect(
                hostname=self.hostname,
                port=self.port,
                username=self.username,
                pkey=private_key,
                timeout=30
            )

            # Create SFTP client for file operations
            self.sftp = self.client.open_sftp()
            logger.info("Successfully connected to AWS instance")
            return True

        except Exception as e:
            logger.error(f"Failed to connect: {str(e)}")
            return False

    def execute_command(self, command: str) -> Dict[str, Any]:
        """
        Execute command on remote server

        Args:
            command: Command to execute

        Returns:
            dict: Contains stdout, stderr, and exit_code
        """
        if not self.client:
            raise Exception("Not connected to server")

        try:
            logger.info(f"Executing: {command}")
            stdin, stdout, stderr = self.client.exec_command(command)

            exit_code = stdout.channel.recv_exit_status()
            stdout_data = stdout.read().decode('utf-8')
            stderr_data = stderr.read().decode('utf-8')

            return {
                'stdout': stdout_data,
                'stderr': stderr_data,
                'exit_code': exit_code
            }
        except Exception as e:
            logger.error(f"Command execution failed: {str(e)}")
            return {'stdout': '', 'stderr': str(e), 'exit_code': -1}

    def list_directory(self, path: str = '/') -> List[Dict[str, Any]]:
        """
        List directory contents with detailed information

        Args:
            path: Directory path to list

        Returns:
            list: List of file/directory information
        """
        try:
            # Execute ls -lrth command
            result = self.execute_command(f"ls -lrth {path}")

            if result['exit_code'] != 0:
                logger.error(f"Failed to list directory: {result['stderr']}")
                return []

            files = []
            lines = result['stdout'].strip().split('\n')

            # Skip the total line if present
            if lines and lines[0].startswith('total'):
                lines = lines[1:]

            for line in lines:
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 9:
                        file_info = {
                            'permissions': parts[0],
                            'links': parts[1],
                            'owner': parts[2],
                            'group': parts[3],
                            'size': parts[4],
                            'month': parts[5],
                            'day': parts[6],
                            'time': parts[7],
                            'name': ' '.join(parts[8:])
                        }
                        files.append(file_info)

            return files
        except Exception as e:
            logger.error(f"Failed to list directory: {str(e)}")
            return []

    def get_file_content(self, remote_path: str) -> Optional[str]:
        """
        Read file content from remote server

        Args:
            remote_path: Path to file on remote server

        Returns:
            str: File content or None if failed
        """
        try:
            with self.sftp.open(remote_path, 'r') as file:
                content = file.read()
                return content
        except Exception as e:
            logger.error(f"Failed to read file {remote_path}: {str(e)}")
            return None

    def download_file(self, remote_path: str, local_path: str) -> bool:
        """
        Download file from remote server

        Args:
            remote_path: Path to file on remote server
            local_path: Local path to save file

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info(f"Downloading {remote_path} to {local_path}")
            self.sftp.get(remote_path, local_path)
            logger.info("Download completed")
            return True
        except Exception as e:
            logger.error(f"Download failed: {str(e)}")
            return False

    def upload_file(self, local_path: str, remote_path: str) -> bool:
        """
        Upload file to remote server

        Args:
            local_path: Local file path
            remote_path: Remote path to save file

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info(f"Uploading {local_path} to {remote_path}")
            self.sftp.put(local_path, remote_path)
            logger.info("Upload completed")
            return True
        except Exception as e:
            logger.error(f"Upload failed: {str(e)}")
            return False

    def change_directory(self, path: str) -> bool:
        """
        Change current directory on remote server

        Args:
            path: Directory path

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            result = self.execute_command(f"cd {path} && pwd")
            if result['exit_code'] == 0:
                logger.info(f"Changed directory to: {result['stdout'].strip()}")
                return True
            else:
                logger.error(f"Failed to change directory: {result['stderr']}")
                return False
        except Exception as e:
            logger.error(f"Failed to change directory: {str(e)}")
            return False

    def get_system_info(self) -> Dict[str, str]:
        """
        Get system information from remote server

        Returns:
            dict: System information
        """
        info = {}
        commands = {
            'hostname': 'hostname',
            'uptime': 'uptime',
            'disk_usage': 'df -h /',
            'memory': 'free -h',
            'cpu_info': 'lscpu | head -10',
            'current_dir': 'pwd',
            'user': 'whoami'
        }

        for key, command in commands.items():
            result = self.execute_command(command)
            if result['exit_code'] == 0:
                info[key] = result['stdout'].strip()
            else:
                info[key] = f"Error: {result['stderr']}"

        return info

    def get_directory_summary(self, path: str) -> Dict[str, Any]:
        """
        Get summary information about a directory

        Args:
            path: Directory path to analyze

        Returns:
            dict: Directory summary with file count, total size, etc.
        """
        try:
            files = self.list_directory(path)
            if not files:
                return {"path": path, "accessible": False, "error": "Directory empty or access denied"}

            total_files = len(files)
            total_dirs = len([f for f in files if f['permissions'].startswith('d')])
            total_regular_files = total_files - total_dirs

            # Calculate total size (only for files with numeric sizes)
            total_size = 0
            size_unit = "bytes"
            for file_info in files:
                size_str = file_info['size']
                if size_str.replace('.', '').isdigit():
                    # Handle sizes like "1.2K", "3.4M", etc.
                    if size_str.endswith('K'):
                        total_size += float(size_str[:-1]) * 1024
                    elif size_str.endswith('M'):
                        total_size += float(size_str[:-1]) * 1024 * 1024
                    elif size_str.endswith('G'):
                        total_size += float(size_str[:-1]) * 1024 * 1024 * 1024
                    else:
                        total_size += float(size_str)

            # Convert to human readable format
            if total_size > 1024 * 1024 * 1024:
                total_size = f"{total_size / (1024 * 1024 * 1024):.1f}GB"
            elif total_size > 1024 * 1024:
                total_size = f"{total_size / (1024 * 1024):.1f}MB"
            elif total_size > 1024:
                total_size = f"{total_size / 1024:.1f}KB"
            else:
                total_size = f"{int(total_size)} bytes"

            return {
                "path": path,
                "accessible": True,
                "total_items": total_files,
                "directories": total_dirs,
                "files": total_regular_files,
                "total_size": total_size,
                "largest_files": sorted(files, key=lambda x: self._parse_size(x['size']), reverse=True)[:3]
            }
        except Exception as e:
            return {"path": path, "accessible": False, "error": str(e)}

    def _parse_size(self, size_str: str) -> float:
        """Parse size string to bytes for sorting"""
        if not size_str or not size_str.replace('.', '').replace('K', '').replace('M', '').replace('G', '').isdigit():
            return 0

        if size_str.endswith('K'):
            return float(size_str[:-1]) * 1024
        elif size_str.endswith('M'):
            return float(size_str[:-1]) * 1024 * 1024
        elif size_str.endswith('G'):
            return float(size_str[:-1]) * 1024 * 1024 * 1024
        else:
            return float(size_str) if size_str.replace('.', '').isdigit() else 0


def get_ssh_config():
    """Get SSH configuration from .env file, command line args, or prompt for missing values"""

    # Set up argument parser
    parser = argparse.ArgumentParser(
        description="Connect to AWS instance via SSH and perform directory operations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Configuration priority (highest to lowest):
  1. Command line arguments
  2. .env file variables
  3. Interactive prompts for missing values

.env file variables:
  AWS_SSH_HOST     - AWS instance hostname/IP
  AWS_SSH_USER     - SSH username (default: forge)
  AWS_SSH_KEY      - Path to SSH private key
  AWS_SSH_PORT     - SSH port (default: 22)

Examples:
  python aws_ssh_client.py                    # Use .env file + prompts
  python aws_ssh_client.py --key ~/.ssh/key   # Override .env SSH key
  python aws_ssh_client.py --verbose          # Enable debug logging
        """
    )

    parser.add_argument(
        "--host", "-H",
        help="Override AWS instance hostname/IP from .env",
        default=None
    )

    parser.add_argument(
        "--user", "-u",
        help="Override SSH username from .env",
        default=None
    )

    parser.add_argument(
        "--key", "-k",
        help="Override SSH private key path from .env",
        default=None
    )

    parser.add_argument(
        "--port", "-p",
        type=int,
        help="Override SSH port from .env",
        default=None
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Get values with priority: CLI args > .env file > defaults
    host = args.host or os.getenv("AWS_SSH_HOST")
    user = args.user or os.getenv("AWS_SSH_USER", "forge")
    key = args.key or os.getenv("AWS_SSH_KEY")
    port = args.port or int(os.getenv("AWS_SSH_PORT", "22"))

    # Check for required values and prompt if missing
    if not host:
        logger.warning("AWS_SSH_HOST not found in .env file")
        host = input("Enter AWS hostname/IP address: ").strip()
        if not host:
            logger.error("Hostname is required")
            sys.exit(1)

    if not key:
        logger.warning("AWS_SSH_KEY not found in .env file")

        # Try to find common SSH key locations
        common_keys = [
            "~/.ssh/id_rsa",
            "~/.ssh/id_ed25519",
            "~/.ssh/aws-key-2025",
            "~/.ssh/id_ecdsa"
        ]

        found_key = None
        for key_path in common_keys:
            expanded_path = Path(key_path).expanduser()
            if expanded_path.exists():
                found_key = str(expanded_path)
                break

        if found_key:
            use_found = input(f"Found SSH key at {found_key}. Use this key? [Y/n]: ").strip().lower()
            if use_found in ['', 'y', 'yes']:
                key = found_key

        if not key:
            key = input("Enter path to SSH private key: ").strip()
            if not key:
                logger.error("SSH key path is required")
                sys.exit(1)

    # Create a simple config object
    class Config:
        def __init__(self, host, user, key, port):
            self.host = host
            self.user = user
            self.key = key
            self.port = port

    return Config(host, user, key, port)


def main():
    """Main function to demonstrate AWS SSH operations"""

    # Get configuration
    config = get_ssh_config()

    print(f"\nConnecting to {config.user}@{config.host}:{config.port}")
    print(f"Using SSH key: {config.key}")
    print("-" * 50)

    # Create SSH client
    ssh_client = AWSSSHClient(config.host, config.user, config.key, config.port)

    try:
        # Connect to server
        if not ssh_client.connect():
            logger.error("Failed to establish connection")
            sys.exit(1)

        # Get system information
        print("\n=== System Information ===")
        system_info = ssh_client.get_system_info()
        for key, value in system_info.items():
            print(f"{key.upper()}: {value}")

        # List home directory
        print("\n=== Home Directory Contents ===")
        home_files = ssh_client.list_directory("/home/forge")
        for file_info in home_files:
            print(f"{file_info['permissions']} {file_info['owner']} {file_info['group']} "
                  f"{file_info['size']} {file_info['month']} {file_info['day']} "
                  f"{file_info['time']} {file_info['name']}")

        # List root directory
        print("\n=== Root Directory Contents ===")
        root_files = ssh_client.list_directory("/")
        for file_info in root_files[:10]:  # Show first 10 items
            print(f"{file_info['permissions']} {file_info['owner']} {file_info['group']} "
                  f"{file_info['size']} {file_info['month']} {file_info['day']} "
                  f"{file_info['time']} {file_info['name']}")

        # Check specific directories from .env configuration
        directories_env = os.getenv("AWS_SSH_DIRECTORIES", "")
        if directories_env:
            directories_to_check = [dir.strip() for dir in directories_env.split(",") if dir.strip()]
        else:
            # Default directories if not specified in .env
            directories_to_check = [
                f"/home/{config.user}",
                "/var/log",
                "/opt"
            ]

        for directory in directories_to_check:
            print(f"\n=== Directory Analysis: {directory} ===")
            summary = ssh_client.get_directory_summary(directory)

            if summary['accessible']:
                print(f"📁 Total items: {summary['total_items']}")
                print(f"📂 Directories: {summary['directories']}")
                print(f"📄 Files: {summary['files']}")
                print(f"💾 Total size: {summary['total_size']}")

                if summary['largest_files']:
                    print("📊 Largest files:")
                    for file_info in summary['largest_files']:
                        print(f"   {file_info['name']} ({file_info['size']})")

                # Show first few items for detailed view
                dir_contents = ssh_client.list_directory(directory)
                if dir_contents:
                    print(f"📋 Recent items (showing first 5):")
                    for file_info in dir_contents[:5]:
                        file_type = "📂" if file_info['permissions'].startswith('d') else "📄"
                        print(
                            f"   {file_type} {file_info['name']} - {file_info['size']} ({file_info['month']} {file_info['day']} {file_info['time']})")
            else:
                print(f"❌ {summary['error']}")

        # Example: Execute custom commands
        print("\n=== Docker Containers (if running) ===")
        docker_result = ssh_client.execute_command("docker ps 2>/dev/null || echo 'Docker not available'")
        if docker_result['exit_code'] == 0 and 'CONTAINER ID' in docker_result['stdout']:
            print("🐳 Running Docker containers:")
            print(docker_result['stdout'])
        else:
            print("🔍 Docker not running or not installed")

        # Show system resources
        print("\n=== System Resources ===")
        resource_commands = {
            "💾 Disk Usage": "df -h / 2>/dev/null | tail -1",
            "🧠 Memory Usage": "free -h 2>/dev/null | grep Mem",
            "⚡ Load Average": "uptime 2>/dev/null | cut -d',' -f3-",
            "🔄 Running Processes": "ps aux --sort=-%cpu | head -5 2>/dev/null || ps aux | head -5"
        }

        for desc, cmd in resource_commands.items():
            result = ssh_client.execute_command(cmd)
            if result['exit_code'] == 0 and result['stdout'].strip():
                print(f"{desc}: {result['stdout'].strip()}")
            else:
                print(f"{desc}: Unable to retrieve")

    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        logger.debug("Full traceback:", exc_info=True)
    finally:
        # Always close the connection safely
        try:
            if 'ssh_client' in locals():
                ssh_client.close()
        except Exception as e:
            logger.debug(f"Error during cleanup: {e}")
            pass  # Don't fail on cleanup errors


if __name__ == "__main__":
    main()