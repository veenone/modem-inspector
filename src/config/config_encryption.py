"""AES-256-GCM encryption for sensitive configuration data.

Provides encryption and decryption of sensitive configuration fields such as
API tokens and passwords.
"""

import os
import base64
from pathlib import Path
from typing import Optional, Dict, Any
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import secrets


class ConfigEncryptionError(Exception):
    """Exception raised for encryption/decryption errors."""
    pass


class ConfigEncryption:
    """AES-256-GCM encryption for sensitive configuration data.

    Provides encryption and decryption of sensitive fields with automatic
    key generation and storage. Supports optional encryption (can be disabled).

    Example:
        >>> # With encryption enabled
        >>> encryption = ConfigEncryption(enabled=True)
        >>> encrypted = encryption.encrypt_value("my-secret-token")
        >>> assert encrypted.startswith("encrypted:")
        >>> decrypted = encryption.decrypt_value(encrypted)
        >>> assert decrypted == "my-secret-token"

        >>> # With encryption disabled
        >>> encryption = ConfigEncryption(enabled=False)
        >>> value = encryption.encrypt_value("my-secret-token")
        >>> assert value == "my-secret-token"  # Returns plaintext
    """

    # Prefix for encrypted values
    ENCRYPTED_PREFIX = "encrypted:"

    # Default key file location
    DEFAULT_KEY_PATH = Path.home() / ".modem-inspector" / ".key"

    def __init__(self,
                 enabled: bool = True,
                 key_path: Optional[Path] = None):
        """Initialize encryption handler.

        Args:
            enabled: Whether encryption is enabled. If False, encrypt/decrypt
                    operations pass through values unchanged.
            key_path: Path to encryption key file. If None, uses default
                     (~/.modem-inspector/.key).

        Raises:
            ConfigEncryptionError: If key file cannot be accessed or created.
        """
        self.enabled = enabled
        self.key_path = key_path or self.DEFAULT_KEY_PATH
        self._key: Optional[bytes] = None

        # Only load/generate key if encryption is enabled
        if self.enabled:
            self._ensure_key()

    def _ensure_key(self):
        """Ensure encryption key exists and is loaded.

        If key file doesn't exist, generates new random AES-256 key and saves
        with 600 permissions (owner read/write only).

        Raises:
            ConfigEncryptionError: If key file cannot be accessed or created.
        """
        try:
            if self.key_path.exists():
                # Load existing key
                self._key = self._load_key()
            else:
                # Generate new key
                self._key = self._generate_key()
                self._save_key(self._key)
        except Exception as e:
            raise ConfigEncryptionError(f"Failed to initialize encryption key: {e}")

    def _generate_key(self) -> bytes:
        """Generate random AES-256 key.

        Returns:
            32-byte random key for AES-256.
        """
        return secrets.token_bytes(32)  # 256 bits

    def _load_key(self) -> bytes:
        """Load encryption key from file.

        Returns:
            Encryption key bytes.

        Raises:
            ConfigEncryptionError: If key file cannot be read.
        """
        try:
            with open(self.key_path, 'rb') as f:
                key_data = f.read()

            # Decode from base64
            key = base64.b64decode(key_data)

            if len(key) != 32:
                raise ConfigEncryptionError(
                    f"Invalid key length: expected 32 bytes, got {len(key)}"
                )

            return key
        except Exception as e:
            raise ConfigEncryptionError(f"Failed to load encryption key: {e}")

    def _save_key(self, key: bytes):
        """Save encryption key to file with 600 permissions.

        Args:
            key: Encryption key bytes to save.

        Raises:
            ConfigEncryptionError: If key file cannot be written.
        """
        try:
            # Create directory if it doesn't exist
            self.key_path.parent.mkdir(parents=True, exist_ok=True)

            # Encode key to base64 for storage
            key_data = base64.b64encode(key)

            # Write key file
            with open(self.key_path, 'wb') as f:
                f.write(key_data)

            # Set permissions to 600 (owner read/write only)
            # On Windows, this may not work as expected, but we try anyway
            try:
                os.chmod(self.key_path, 0o600)
            except (OSError, NotImplementedError):
                # Windows doesn't support chmod in the same way
                # We'll rely on NTFS permissions instead
                pass

        except Exception as e:
            raise ConfigEncryptionError(f"Failed to save encryption key: {e}")

    def encrypt_value(self, plaintext: str) -> str:
        """Encrypt a plaintext value.

        Args:
            plaintext: Plain text string to encrypt.

        Returns:
            Encrypted value in format "encrypted:BASE64_DATA" if encryption
            is enabled, or original plaintext if encryption is disabled.

        Example:
            >>> encryption = ConfigEncryption(enabled=True)
            >>> encrypted = encryption.encrypt_value("secret123")
            >>> assert encrypted.startswith("encrypted:")
        """
        # If encryption is disabled, return plaintext
        if not self.enabled:
            return plaintext

        if not plaintext:
            return plaintext

        try:
            # Convert plaintext to bytes
            plaintext_bytes = plaintext.encode('utf-8')

            # Generate random 12-byte nonce (96 bits, recommended for GCM)
            nonce = secrets.token_bytes(12)

            # Create AESGCM cipher
            aesgcm = AESGCM(self._key)

            # Encrypt (includes authentication tag)
            ciphertext = aesgcm.encrypt(nonce, plaintext_bytes, None)

            # Combine nonce + ciphertext for storage
            encrypted_data = nonce + ciphertext

            # Encode to base64
            encoded = base64.b64encode(encrypted_data).decode('ascii')

            return f"{self.ENCRYPTED_PREFIX}{encoded}"

        except Exception as e:
            raise ConfigEncryptionError(f"Failed to encrypt value: {e}")

    def decrypt_value(self, encrypted: str) -> str:
        """Decrypt an encrypted value.

        Args:
            encrypted: Encrypted value in format "encrypted:BASE64_DATA".

        Returns:
            Decrypted plaintext string if encryption is enabled, or original
            value if encryption is disabled or value is not encrypted.

        Raises:
            ConfigEncryptionError: If decryption fails or key is missing.

        Example:
            >>> encryption = ConfigEncryption(enabled=True)
            >>> encrypted = encryption.encrypt_value("secret123")
            >>> decrypted = encryption.decrypt_value(encrypted)
            >>> assert decrypted == "secret123"
        """
        # If encryption is disabled, return value as-is
        if not self.enabled:
            return encrypted

        # If value is not encrypted, return as-is
        if not self.is_encrypted(encrypted):
            return encrypted

        if self._key is None:
            raise ConfigEncryptionError(
                "Encryption key not loaded. Cannot decrypt sensitive fields."
            )

        try:
            # Remove prefix and decode from base64
            encoded = encrypted[len(self.ENCRYPTED_PREFIX):]
            encrypted_data = base64.b64decode(encoded)

            # Split nonce and ciphertext
            nonce = encrypted_data[:12]
            ciphertext = encrypted_data[12:]

            # Create AESGCM cipher
            aesgcm = AESGCM(self._key)

            # Decrypt and verify authentication tag
            plaintext_bytes = aesgcm.decrypt(nonce, ciphertext, None)

            # Convert bytes to string
            return plaintext_bytes.decode('utf-8')

        except Exception as e:
            raise ConfigEncryptionError(f"Failed to decrypt value: {e}")

    def is_encrypted(self, value: str) -> bool:
        """Check if a value is encrypted.

        Args:
            value: Value to check.

        Returns:
            True if value starts with "encrypted:" prefix, False otherwise.

        Example:
            >>> encryption = ConfigEncryption()
            >>> assert encryption.is_encrypted("encrypted:abc123")
            >>> assert not encryption.is_encrypted("plaintext")
        """
        if not value or not isinstance(value, str):
            return False

        return value.startswith(self.ENCRYPTED_PREFIX)

    def rotate_key(self, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Rotate encryption key and re-encrypt all sensitive fields.

        Generates new encryption key, re-encrypts all encrypted values in
        configuration dictionary, and saves new key.

        Args:
            config_dict: Configuration dictionary with encrypted values.

        Returns:
            Configuration dictionary with values re-encrypted using new key.

        Raises:
            ConfigEncryptionError: If key rotation fails.

        Example:
            >>> encryption = ConfigEncryption(enabled=True)
            >>> config = {"repository": {"api_token": "encrypted:..."}}
            >>> rotated = encryption.rotate_key(config)
        """
        if not self.enabled:
            # If encryption is disabled, return config unchanged
            return config_dict

        try:
            # Store old key
            old_key = self._key

            # Generate new key
            new_key = self._generate_key()

            # Create temporary encryption instance with old key for decryption
            old_encryption = ConfigEncryption(enabled=True, key_path=self.key_path)
            old_encryption._key = old_key

            # Set new key for this instance (for encryption)
            self._key = new_key

            # Recursively re-encrypt all encrypted values
            rotated_config = self._rotate_dict(config_dict, old_encryption)

            # Save new key
            self._save_key(new_key)

            return rotated_config

        except Exception as e:
            # Restore old key on error
            self._key = old_key
            raise ConfigEncryptionError(f"Failed to rotate encryption key: {e}")

    def _rotate_dict(self, data: Any, old_encryption: 'ConfigEncryption') -> Any:
        """Recursively re-encrypt encrypted values in nested dictionary.

        Args:
            data: Data to process (dict, list, or value).
            old_encryption: Encryption instance with old key for decryption.

        Returns:
            Data with re-encrypted values.
        """
        if isinstance(data, dict):
            return {
                key: self._rotate_dict(value, old_encryption)
                for key, value in data.items()
            }
        elif isinstance(data, list):
            return [self._rotate_dict(item, old_encryption) for item in data]
        elif isinstance(data, str) and self.is_encrypted(data):
            # Decrypt with old key, encrypt with new key
            plaintext = old_encryption.decrypt_value(data)
            return self.encrypt_value(plaintext)
        else:
            return data

    def decrypt_sensitive_fields(self, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Decrypt all sensitive fields in configuration dictionary.

        Recursively finds and decrypts all encrypted values in configuration.

        Args:
            config_dict: Configuration dictionary with encrypted values.

        Returns:
            Configuration dictionary with decrypted values.

        Example:
            >>> encryption = ConfigEncryption(enabled=True)
            >>> config = {"repository": {"api_token": "encrypted:abc123"}}
            >>> decrypted = encryption.decrypt_sensitive_fields(config)
            >>> assert not decrypted["repository"]["api_token"].startswith("encrypted:")
        """
        if not self.enabled:
            # If encryption is disabled, return config unchanged
            return config_dict

        return self._decrypt_dict(config_dict)

    def _decrypt_dict(self, data: Any) -> Any:
        """Recursively decrypt encrypted values in nested dictionary.

        Args:
            data: Data to process (dict, list, or value).

        Returns:
            Data with decrypted values.
        """
        if isinstance(data, dict):
            return {
                key: self._decrypt_dict(value)
                for key, value in data.items()
            }
        elif isinstance(data, list):
            return [self._decrypt_dict(item) for item in data]
        elif isinstance(data, str) and self.is_encrypted(data):
            return self.decrypt_value(data)
        else:
            return data

    def encrypt_sensitive_fields(self,
                                 config_dict: Dict[str, Any],
                                 sensitive_keys: list = None) -> Dict[str, Any]:
        """Encrypt sensitive fields in configuration dictionary.

        Args:
            config_dict: Configuration dictionary to encrypt.
            sensitive_keys: List of key names to encrypt (e.g., ['api_token', 'password']).
                           If None, uses default list.

        Returns:
            Configuration dictionary with encrypted sensitive fields.

        Example:
            >>> encryption = ConfigEncryption(enabled=True)
            >>> config = {"repository": {"api_token": "secret123"}}
            >>> encrypted = encryption.encrypt_sensitive_fields(config)
            >>> assert encrypted["repository"]["api_token"].startswith("encrypted:")
        """
        if not self.enabled:
            # If encryption is disabled, return config unchanged
            return config_dict

        if sensitive_keys is None:
            # Default sensitive field names
            sensitive_keys = ['api_token', 'api_password', 'password', 'secret', 'key']

        return self._encrypt_dict(config_dict, sensitive_keys)

    def _encrypt_dict(self, data: Any, sensitive_keys: list) -> Any:
        """Recursively encrypt sensitive values in nested dictionary.

        Args:
            data: Data to process (dict, list, or value).
            sensitive_keys: List of key names to encrypt.

        Returns:
            Data with encrypted sensitive values.
        """
        if isinstance(data, dict):
            result = {}
            for key, value in data.items():
                if key in sensitive_keys and isinstance(value, str) and not self.is_encrypted(value):
                    # Encrypt this value
                    result[key] = self.encrypt_value(value)
                else:
                    # Recurse into nested structures
                    result[key] = self._encrypt_dict(value, sensitive_keys)
            return result
        elif isinstance(data, list):
            return [self._encrypt_dict(item, sensitive_keys) for item in data]
        else:
            return data
