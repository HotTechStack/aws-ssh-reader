# AWS SSH Directory Access Script

A Python script to connect to AWS instances via SSH and perform directory operations using the `uv` package manager.

## Setup Instructions

### 1. Install uv package manager (if not already installed)

```bash
# On macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# On Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Or using pip
pip install uv
```


### 2. Install dependencies using uv

```bash
# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e .
```

### 3. Update .env configuration file

Create a `.env` file in your project directory:

```bash
# Copy the .env template and edit it
cp .env.example .env
```


### 6. Run the script

```bash
# Simple - uses .env file configuration
python aws_ssh_client.py

# Override specific values from .env
python aws_ssh_client.py --key ~/.ssh/different-key

# Enable verbose logging
python aws_ssh_client.py --verbose
```

## Usage Examples

### Basic Usage

```bash
# Use .env file configuration (recommended)
python aws_ssh_client.py

# Override specific values from .env file
python aws_ssh_client.py --key ~/.ssh/different-key
python aws_ssh_client.py --host different-server.com

# Enable verbose logging
python aws_ssh_client.py --verbose

# If .env values are missing, script will prompt interactively
python aws_ssh_client.py
# AWS_SSH_HOST not found in .env file
# Enter AWS hostname/IP address: 34.229.96.55
```

### Configuration Priority

The script uses this priority order:

1. **Command line arguments** (highest priority)
2. **.env file variables**
3. **Interactive prompts** (only if values are missing)

### .env File Format

Create a `.env` file in your project root:

```bash
# Required values
AWS_SSH_HOST=34.229.96.55
AWS_SSH_KEY=~/.ssh/aws-key-2025

# Optional values (with defaults)
AWS_SSH_USER=forge
AWS_SSH_PORT=22
```


## Environment Configuration

### .env File (Recommended)

Create a `.env` file in your project root with your AWS configuration:

```bash
# Required
AWS_SSH_HOST=34.229.96.55
AWS_SSH_KEY=~/.ssh/aws-key-2025

# Optional (with defaults)
AWS_SSH_USER=forge
AWS_SSH_PORT=22
```

### Missing Configuration Handling

- **Script alerts you**: If required values are missing from `.env`, you'll see warnings
- **Interactive prompts**: Only appears for missing required values
- **Auto-detection**: Automatically finds common SSH keys if not specified
- **Clean fallback**: No hardcoded values in the script

### Security Best Practices

1. **Add .env to .gitignore**:
   ```bash
   echo ".env" >> .gitignore
   ```

2. **Set proper SSH key permissions**:
   ```bash
   chmod 600 ~/.ssh/aws-key-2025
   ```

3. **Use SSH agent** (optional):
   ```bash
   ssh-add ~/.ssh/aws-key-2025
   ```

## Security Notes

1. **SSH Key Protection**: Ensure your SSH private key has proper permissions (600)
   ```bash
   chmod 600 ~/.ssh/aws-key-2025
   ```

2. **Key Management**: Consider using SSH agent for better key management
   ```bash
   ssh-add ~/.ssh/aws-key-2025
   ```

3. **Connection Security**: The script uses paramiko with proper host key checking

## Development

### Running with development dependencies

```bash
# Install with dev dependencies
uv pip install -e ".[dev]"

# Format code
black aws_ssh_client.py

# Sort imports
isort aws_ssh_client.py

# Type checking
mypy aws_ssh_client.py

# Run tests
pytest
```

## Troubleshooting

### Common Issues

1. **Permission Denied**: Check SSH key permissions and username
2. **Connection Timeout**: Verify AWS security groups allow SSH access
3. **Host Key Verification**: The script automatically adds unknown host keys
4. **Module Import Error**: Ensure you're in the activated virtual environment

### Debugging

Enable debug logging by modifying the logging level:

```python
logging.basicConfig(level=logging.DEBUG)
```

This will show detailed SSH connection information and command execution details.