import os
import sys
import json
import time
import threading
from pathlib import Path
from datetime import datetime
import requests
import boto3
from botocore.exceptions import ClientError
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from tqdm import tqdm
import humanize
import dropbox
from dropbox.exceptions import AuthError, ApiError
from dropbox.files import WriteMode


class CloudBackupService:
    """Base class for cloud backup services"""
    
    def __init__(self, config_dir=None):
        # Create a config directory in user's home folder if not specified
        if config_dir is None:
            self.config_dir = Path.home() / ".photo_organizer" / "cloud_config"
        else:
            self.config_dir = Path(config_dir)
            
        # Create directory if it doesn't exist
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.is_authenticated = False
        
    def authenticate(self):
        """Authenticate with the cloud service"""
        raise NotImplementedError("Subclasses must implement authenticate()")
    
    def upload_file(self, file_path, remote_path):
        """Upload a single file to the cloud service"""
        raise NotImplementedError("Subclasses must implement upload_file()")
    
    def upload_directory(self, local_dir, remote_dir, progress_callback=None):
        """Upload a directory to the cloud service"""
        raise NotImplementedError("Subclasses must implement upload_directory()")
    
    def list_backups(self):
        """List available backups"""
        raise NotImplementedError("Subclasses must implement list_backups()")
    
    def download_backup(self, backup_id, destination_dir, progress_callback=None):
        """Download a backup to local storage"""
        raise NotImplementedError("Subclasses must implement download_backup()")


class DropboxBackup(CloudBackupService):
    """Dropbox backup service"""
    
    def __init__(self, config_dir=None, app_key=None):
        super().__init__(config_dir)
        self.app_key = app_key
        self.token_file = self.config_dir / "dropbox_token.json"
        self.dbx = None
        
        # Load token if exists
        if self.token_file.exists():
            try:
                with open(self.token_file, 'r') as f:
                    token_data = json.load(f)
                    if 'access_token' in token_data and 'refresh_token' in token_data:
                        self.access_token = token_data['access_token']
                        self.refresh_token = token_data['refresh_token']
                        self.token_expiry = token_data.get('expiry', 0)
                        
                        # Check if token is expired and needs refresh
                        if self.token_expiry < time.time():
                            self._refresh_token()
                        else:
                            self.dbx = dropbox.Dropbox(self.access_token)
                            self.is_authenticated = True
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Error loading Dropbox token: {e}")
    
    def _refresh_token(self):
        """Refresh the access token using refresh token"""
        try:
            # This is a simplified version. In production, use refresh token API
            self.dbx = dropbox.Dropbox(
                oauth2_refresh_token=self.refresh_token,
                app_key=self.app_key
            )
            self.access_token = self.dbx._oauth2_access_token
            self.is_authenticated = True
            
            # Save the new token
            token_data = {
                'access_token': self.access_token,
                'refresh_token': self.refresh_token,
                'expiry': int(time.time()) + 14000  # ~4 hours
            }
            
            with open(self.token_file, 'w') as f:
                json.dump(token_data, f)
                
        except Exception as e:
            print(f"Error refreshing Dropbox token: {e}")
            self.is_authenticated = False
    
    def authenticate(self):
        """Authenticate with Dropbox"""
        if not self.app_key:
            raise ValueError("Dropbox app key is required")
            
        auth_flow = dropbox.DropboxOAuth2FlowNoRedirect(
            self.app_key,
            use_pkce=True,
            token_access_type='offline'
        )
        
        auth_url = auth_flow.start()
        print("1. Go to this URL:", auth_url)
        print("2. Click 'Allow' to grant access to your Dropbox")
        print("3. Copy the authorization code")
        auth_code = input("Enter the authorization code: ").strip()
        
        try:
            # Exchange auth code for access token
            oauth_result = auth_flow.finish(auth_code)
            self.access_token = oauth_result.access_token
            self.refresh_token = oauth_result.refresh_token
            
            # Save token info
            token_data = {
                'access_token': self.access_token,
                'refresh_token': self.refresh_token,
                'expiry': int(time.time()) + 14000  # ~4 hours
            }
            
            with open(self.token_file, 'w') as f:
                json.dump(token_data, f)
            
            # Initialize Dropbox client
            self.dbx = dropbox.Dropbox(self.access_token)
            self.is_authenticated = True
            print("Successfully authenticated with Dropbox!")
            return True
            
        except Exception as e:
            print(f"Error authenticating with Dropbox: {e}")
            return False
    
    def upload_file(self, file_path, remote_path=None):
        """Upload a single file to Dropbox"""
        if not self.is_authenticated:
            print("Not authenticated. Call authenticate() first.")
            return False
        
        file_path = Path(file_path)
        if not file_path.exists():
            print(f"File not found: {file_path}")
            return False
        
        # If remote path not specified, use filename
        if remote_path is None:
            remote_path = f"/Photo_Organizer_Backup/{file_path.name}"
        
        # Make sure remote path starts with /
        if not remote_path.startswith('/'):
            remote_path = '/' + remote_path
        
        try:
            print(f"Uploading {file_path} to Dropbox...")
            
            # Read file in chunks
            with open(file_path, 'rb') as f:
                file_size = file_path.stat().st_size
                
                # Use upload_session for larger files
                if file_size > 8 * 1024 * 1024:  # 8 MB
                    chunk_size = 4 * 1024 * 1024  # 4 MB chunks
                    upload_session_start_result = self.dbx.files_upload_session_start(f.read(chunk_size))
                    cursor = dropbox.files.UploadSessionCursor(
                        session_id=upload_session_start_result.session_id,
                        offset=f.tell()
                    )
                    
                    commit = dropbox.files.CommitInfo(
                        path=remote_path,
                        mode=WriteMode('overwrite')
                    )
                    
                    # Upload remaining data in chunks
                    while f.tell() < file_size:
                        # If we're close to the end of the file, finish upload
                        if (file_size - f.tell()) <= chunk_size:
                            self.dbx.files_upload_session_finish(
                                f.read(chunk_size),
                                cursor,
                                commit
                            )
                        else:
                            self.dbx.files_upload_session_append_v2(
                                f.read(chunk_size),
                                cursor
                            )
                            cursor.offset = f.tell()
                else:
                    # For smaller files, direct upload
                    self.dbx.files_upload(
                        f.read(),
                        remote_path,
                        mode=WriteMode('overwrite')
                    )
            
            print(f"Successfully uploaded {file_path} to Dropbox")
            return True
            
        except ApiError as e:
            print(f"Dropbox API error: {e}")
            return False
        except Exception as e:
            print(f"Error uploading file to Dropbox: {e}")
            return False
    
    def upload_directory(self, local_dir, remote_dir=None, progress_callback=None):
        """Upload a directory to Dropbox"""
        if not self.is_authenticated:
            print("Not authenticated. Call authenticate() first.")
            return False
        
        local_dir = Path(local_dir)
        if not local_dir.exists():
            print(f"Directory not found: {local_dir}")
            return False
        
        # If remote directory not specified, use local directory name
        if remote_dir is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            remote_dir = f"/Photo_Organizer_Backup/{local_dir.name}_{timestamp}"
        
        # Make sure remote path starts with /
        if not remote_dir.startswith('/'):
            remote_dir = '/' + remote_dir
        
        # Get list of files to upload
        files_to_upload = []
        total_size = 0
        
        for file_path in local_dir.rglob('*'):
            if file_path.is_file():
                # Calculate relative path for remote
                rel_path = file_path.relative_to(local_dir)
                remote_path = f"{remote_dir}/{rel_path}"
                files_to_upload.append((file_path, remote_path))
                total_size += file_path.stat().st_size
        
        if not files_to_upload:
            print(f"No files found in {local_dir}")
            return False
        
        print(f"Found {len(files_to_upload)} files to upload ({humanize.naturalsize(total_size)})")
        
        # Create progress bar if no callback provided
        if progress_callback is None:
            progress = tqdm(total=total_size, unit='B', unit_scale=True)
        
        # Upload files
        uploaded_size = 0
        failed_files = []
        
        for file_path, remote_path in files_to_upload:
            try:
                file_size = file_path.stat().st_size
                
                # Ensure parent directory exists
                parent_dir = Path(remote_path).parent
                try:
                    self.dbx.files_create_folder_v2(str(parent_dir))
                except ApiError:
                    # Folder might already exist, which is fine
                    pass
                
                # Upload file
                with open(file_path, 'rb') as f:
                    self.dbx.files_upload(
                        f.read(),
                        remote_path,
                        mode=WriteMode('overwrite')
                    )
                
                uploaded_size += file_size
                
                # Update progress
                if progress_callback:
                    progress_callback(uploaded_size, total_size)
                else:
                    progress.update(file_size)
                    
            except Exception as e:
                print(f"\nError uploading {file_path}: {e}")
                failed_files.append(file_path)
        
        # Close progress bar if we created it
        if progress_callback is None:
            progress.close()
        
        # Print summary
        print("\nUpload Summary:")
        print(f"Total files: {len(files_to_upload)}")
        print(f"Successfully uploaded: {len(files_to_upload) - len(failed_files)}")
        print(f"Failed: {len(failed_files)}")
        
        if failed_files:
            print("\nFailed files:")
            for file in failed_files[:10]:  # Show first 10
                print(f"- {file}")
            if len(failed_files) > 10:
                print(f"... and {len(failed_files) - 10} more")
        
        return len(failed_files) == 0
    
    def list_backups(self):
        """List available backups in Dropbox"""
        if not self.is_authenticated:
            print("Not authenticated. Call authenticate() first.")
            return []
        
        try:
            result = self.dbx.files_list_folder("/Photo_Organizer_Backup")
            backups = []
            
            for entry in result.entries:
                if isinstance(entry, dropbox.files.FolderMetadata):
                    backups.append({
                        'id': entry.id,
                        'name': entry.name,
                        'path': entry.path_display
                    })
            
            # Continue if there are more results
            while result.has_more:
                result = self.dbx.files_list_folder_continue(result.cursor)
                for entry in result.entries:
                    if isinstance(entry, dropbox.files.FolderMetadata):
                        backups.append({
                            'id': entry.id,
                            'name': entry.name,
                            'path': entry.path_display
                        })
            
            return backups
            
        except ApiError as e:
            if e.error.is_path() and e.error.get_path().is_not_found():
                # Backup directory doesn't exist yet
                return []
            print(f"Dropbox API error: {e}")
            return []
        except Exception as e:
            print(f"Error listing backups: {e}")
            return []
    
    def download_backup(self, backup_path, destination_dir, progress_callback=None):
        """Download a backup from Dropbox"""
        if not self.is_authenticated:
            print("Not authenticated. Call authenticate() first.")
            return False
        
        destination_dir = Path(destination_dir)
        destination_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # List all files in the backup
            files_to_download = []
            result = self.dbx.files_list_folder(backup_path, recursive=True)
            
            # Collect all files
            for entry in result.entries:
                if isinstance(entry, dropbox.files.FileMetadata):
                    files_to_download.append({
                        'path': entry.path_display,
                        'size': entry.size
                    })
            
            # Continue if there are more results
            while result.has_more:
                result = self.dbx.files_list_folder_continue(result.cursor)
                for entry in result.entries:
                    if isinstance(entry, dropbox.files.FileMetadata):
                        files_to_download.append({
                            'path': entry.path_display,
                            'size': entry.size
                        })
            
            if not files_to_download:
                print(f"No files found in backup {backup_path}")
                return False
            
            # Calculate total size
            total_size = sum(file['size'] for file in files_to_download)
            print(f"Found {len(files_to_download)} files to download ({humanize.naturalsize(total_size)})")
            
            # Create progress bar if no callback provided
            if progress_callback is None:
                progress = tqdm(total=total_size, unit='B', unit_scale=True)
            
            # Download files
            downloaded_size = 0
            failed_files = []
            
            for file_info in files_to_download:
                try:
                    # Calculate local path
                    rel_path = Path(file_info['path']).relative_to(Path(backup_path))
                    local_path = destination_dir / rel_path
                    
                    # Create parent directory if needed
                    local_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Download file
                    metadata, response = self.dbx.files_download(file_info['path'])
                    
                    with open(local_path, 'wb') as f:
                        f.write(response.content)
                    
                    downloaded_size += file_info['size']
                    
                    # Update progress
                    if progress_callback:
                        progress_callback(downloaded_size, total_size)
                    else:
                        progress.update(file_info['size'])
                        
                except Exception as e:
                    print(f"\nError downloading {file_info['path']}: {e}")
                    failed_files.append(file_info['path'])
            
            # Close progress bar if we created it
            if progress_callback is None:
                progress.close()
            
            # Print summary
            print("\nDownload Summary:")
            print(f"Total files: {len(files_to_download)}")
            print(f"Successfully downloaded: {len(files_to_download) - len(failed_files)}")
            print(f"Failed: {len(failed_files)}")
            
            if failed_files:
                print("\nFailed files:")
                for file in failed_files[:10]:  # Show first 10
                    print(f"- {file}")
                if len(failed_files) > 10:
                    print(f"... and {len(failed_files) - 10} more")
            
            return len(failed_files) == 0
            
        except ApiError as e:
            print(f"Dropbox API error: {e}")
            return False
        except Exception as e:
            print(f"Error downloading backup: {e}")
            return False
            

class GoogleDriveBackup(CloudBackupService):
    """Google Drive backup service"""
    
    def __init__(self, config_dir=None, credentials_file=None):
        super().__init__(config_dir)
        self.credentials_file = credentials_file
        self.token_file = self.config_dir / "gdrive_token.json"
        self.drive = None
        self.SCOPES = ['https://www.googleapis.com/auth/drive.file']
        
        # Try to load saved credentials
        if self.token_file.exists():
            try:
                creds = Credentials.from_authorized_user_info(
                    json.loads(self.token_file.read_text()), 
                    self.SCOPES
                )
                
                if creds and not creds.expired:
                    self.drive_service = build('drive', 'v3', credentials=creds)
                    self.credentials = creds
                    self.is_authenticated = True
            except Exception as e:
                print(f"Error loading Google Drive credentials: {e}")
    
    def authenticate(self):
        """Authenticate with Google Drive"""
        if not self.credentials_file:
            raise ValueError("Google Drive credentials file is required")
        
        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                self.credentials_file, 
                self.SCOPES
            )
            creds = flow.run_local_server(port=0)
            
            # Save credentials
            self.token_file.write_text(creds.to_json())
            self.credentials = creds
            
            # Initialize Drive service
            self.drive_service = build('drive', 'v3', credentials=creds)
            self.is_authenticated = True
            print("Successfully authenticated with Google Drive!")
            return True
            
        except Exception as e:
            print(f"Error authenticating with Google Drive: {e}")
            return False
    
    def get_or_create_folder(self, folder_name, parent_id=None):
        """Get folder ID by name, create if not exists"""
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'"
        if parent_id:
            query += f" and '{parent_id}' in parents"
        query += " and trashed=false"
        
        response = self.drive_service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name)'
        ).execute()
        
        folders = response.get('files', [])
        
        # If folder exists, return its ID
        if folders:
            return folders[0]['id']
        
        # Folder doesn't exist, create it
        folder_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        
        if parent_id:
            folder_metadata['parents'] = [parent_id]
        
        folder = self.drive_service.files().create(
            body=folder_metadata,
            fields='id'
        ).execute()
        
        return folder.get('id')
    
    def upload_file(self, file_path, remote_folder_id=None, remote_filename=None):
        """Upload a single file to Google Drive"""
        if not self.is_authenticated:
            print("Not authenticated. Call authenticate() first.")
            return False
        
        file_path = Path(file_path)
        if not file_path.exists():
            print(f"File not found: {file_path}")
            return False
        
        # Get or create backup folder
        if remote_folder_id is None:
            remote_folder_id = self.get_or_create_folder('Photo_Organizer_Backup')
        
        # Use original filename if not specified
        if remote_filename is None:
            remote_filename = file_path.name
        
        try:
            # File metadata
            file_metadata = {
                'name': remote_filename,
                'parents': [remote_folder_id]
            }
            
            # Upload file
            media = MediaFileUpload(
                str(file_path),
                resumable=True
            )
            
            file = self.drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            print(f"Successfully uploaded {file_path} to Google Drive")
            return file.get('id')
            
        except HttpError as e:
            print(f"Google Drive API error: {e}")
            return False
        except Exception as e:
            print(f"Error uploading file to Google Drive: {e}")
            return False
    
    def upload_directory(self, local_dir, remote_folder_name=None, progress_callback=None):
        """Upload a directory to Google Drive"""
        if not self.is_authenticated:
            print("Not authenticated. Call authenticate() first.")
            return False
        
        local_dir = Path(local_dir)
        if not local_dir.exists():
            print(f"Directory not found: {local_dir}")
            return False
        
        # Create backup root folder if it doesn't exist
        backup_folder_id = self.get_or_create_folder('Photo_Organizer_Backup')
        
        # Create folder for this backup
        if remote_folder_name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            remote_folder_name = f"{local_dir.name}_{timestamp}"
        
        backup_dir_id = self.get_or_create_folder(remote_folder_name, backup_folder_id)
        
        # Get list of files to upload
        files_to_upload = []
        folder_structure = {}
        total_size = 0
        
        for file_path in local_dir.rglob('*'):
            if file_path.is_file():
                # Calculate relative path for remote
                rel_path = file_path.relative_to(local_dir)
                # Get parent folders
                parent_folders = list(rel_path.parents)
                parent_folders.reverse()  # Start from top level
                
                # Add file to upload list
                file_size = file_path.stat().st_size
                files_to_upload.append({
                    'path': file_path,
                    'rel_path': rel_path,
                    'size': file_size
                })
                total_size += file_size
                
                # Remember folder structure
                current_parent = backup_dir_id
                for folder in parent_folders:
                    if folder.name != '':  # Skip top level '.'
                        folder_key = f"{current_parent}:{folder.name}"
                        if folder_key not in folder_structure:
                            # We'll create this folder later and store its ID
                            folder_structure[folder_key] = {
                                'parent_id': current_parent,
                                'name': folder.name,
                                'id': None
                            }
                        # Move down a level
                        if folder_structure[folder_key]['id']:
                            current_parent = folder_structure[folder_key]['id']
                        else:
                            # Placeholder, will be updated once folder is created
                            current_parent = folder_key
        
        if not files_to_upload:
            print(f"No files found in {local_dir}")
            return False
        
        print(f"Found {len(files_to_upload)} files to upload ({humanize.naturalsize(total_size)})")
        
        # Create folder structure first
        print("Creating folder structure...")
        folder_id_mapping = {backup_dir_id: backup_dir_id}  # Map for resolving placeholders
        
        # Keep processing until all folders have IDs
        while any(folder['id'] is None for folder in folder_structure.values()):
            for folder_key, folder_info in folder_structure.items():
                if folder_info['id'] is None:
                    # Check if parent is ready (has an ID)
                    parent_id = folder_info['parent_id']
                    if parent_id in folder_id_mapping:
                        # Parent is ready, create this folder
                        actual_parent_id = folder_id_mapping[parent_id]
                        folder_id = self.get_or_create_folder(folder_info['name'], actual_parent_id)
                        folder_info['id'] = folder_id
                        folder_id_mapping[folder_key] = folder_id
        
        # Create progress bar if no callback provided
        if progress_callback is None:
            progress = tqdm(total=total_size, unit='B', unit_scale=True)
        
        # Upload files
        uploaded_size = 0
        failed_files = []
        
        for file_info in files_to_upload:
            try:
                # Determine parent folder ID for this file
                parent_id = backup_dir_id
                if file_info['rel_path'].parent.name != '':
                    # File is in a subfolder
                    parent_key = None
                    for folder_key, folder_info in folder_structure.items():
                        if folder_info['name'] == file_info['rel_path'].parent.name:
                            parent_key = folder_key
                            break
                    
                    if parent_key and folder_structure[parent_key]['id']:
                        parent_id = folder_structure[parent_key]['id']
                
                # File metadata
                file_metadata = {
                    'name': file_info['rel_path'].name,
                    'parents': [parent_id]
                }
                
                # Upload file
                media = MediaFileUpload(
                    str(file_info['path']),
                    resumable=True
                )
                
                file = self.drive_service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id'
                ).execute()
                
                uploaded_size += file_info['size']
                
                # Update progress
                if progress_callback:
                    progress_callback(uploaded_size, total_size)
                else:
                    progress.update(file_info['size'])
                
            except Exception as e:
                print(f"\nError uploading {file_info['path']}: {e}")
                failed_files.append(file_info['path'])
        
        # Close progress bar if we created it
        if progress_callback is None:
            progress.close()
        
        # Print summary
        print("\nUpload Summary:")
        print(f"Total files: {len(files_to_upload)}")
        print(f"Successfully uploaded: {len(files_to_upload) - len(failed_files)}")
        print(f"Failed: {len(failed_files)}")
        
        if failed_files:
            print("\nFailed files:")
            for file in failed_files[:10]:  # Show first 10
                print(f"- {file}")
            if len(failed_files) > 10:
                print(f"... and {len(failed_files) - 10} more")
        
        return len(failed_files) == 0
    
    def list_backups(self):
        """List available backups in Google Drive"""
        if not self.is_authenticated:
            print("Not authenticated. Call authenticate() first.")
            return []
        
        try:
            # First get the backup root folder
            query = "name='Photo_Organizer_Backup' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            response = self.drive_service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)'
            ).execute()
            
            folders = response.get('files', [])
            if not folders:
                return []
            
            root_folder_id = folders[0]['id']
            
            # Now get all backup folders inside the root
            query = f"'{root_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
            response = self.drive_service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name, createdTime)'
            ).execute()
            
            backups = []
            for folder in response.get('files', []):
                backups.append({
                    'id': folder['id'],
                    'name': folder['name'],
                    'created': folder['createdTime']
                })
            
            return backups
            
        except HttpError as e:
            print(f"Google Drive API error: {e}")
            return []
        except Exception as e:
            print(f"Error listing backups: {e}")
            return []
    
    def download_backup(self, backup_id, destination_dir, progress_callback=None):
        """Download a backup from Google Drive"""
        if not self.is_authenticated:
            print("Not authenticated. Call authenticate() first.")
            return False
        
        destination_dir = Path(destination_dir)
        destination_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Get all files in the backup folder (recursive)
            files_to_download = []
            
            # First get immediate children
            query = f"'{backup_id}' in parents and trashed=false"
            response = self.drive_service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name, mimeType, size)',
                pageSize=1000
            ).execute()
            
            # Process response
            files = response.get('files', [])
            folders = [f for f in files if f['mimeType'] == 'application/vnd.google-apps.folder']
            direct_files = [f for f in files if f['mimeType'] != 'application/vnd.google-apps.folder']
            
            # Add direct files to download list
            for file in direct_files:
                files_to_download.append({
                    'id': file['id'],
                    'name': file['name'],
                    'size': int(file.get('size', 0)),
                    'path': file['name']
                })
            
            # Get files in subfolders (recursive)
            for folder in folders:
                folder_path = folder['name']
                self._get_files_recursive(folder['id'], folder_path, files_to_download)
            
            if not files_to_download:
                print(f"No files found in backup {backup_id}")
                return False
            
            # Calculate total size
            total_size = sum(file['size'] for file in files_to_download)
            print(f"Found {len(files_to_download)} files to download ({humanize.naturalsize(total_size)})")
            
            # Create progress bar if no callback provided
            if progress_callback is None:
                progress = tqdm(total=total_size, unit='B', unit_scale=True)
            
            # Download files
            downloaded_size = 0
            failed_files = []
            
            for file_info in files_to_download:
                try:
                    # Calculate local path
                    local_path = destination_dir / file_info['path']
                    
                    # Create parent directory if needed
                    local_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Download file
                    request = self.drive_service.files().get_media(fileId=file_info['id'])
                    with open(local_path, 'wb') as f:
                        downloader = MediaIoBaseDownload(f, request)
                        done = False
                        while not done:
                            status, done = downloader.next_chunk()
                    
                    downloaded_size += file_info['size']
                    
                    # Update progress
                    if progress_callback:
                        progress_callback(downloaded_size, total_size)
                    else:
                        progress.update(file_info['size'])
                        
                except Exception as e:
                    print(f"\nError downloading {file_info['path']}: {e}")
                    failed_files.append(file_info['path'])
            
            # Close progress bar if we created it
            if progress_callback is None:
                progress.close()
            
            # Print summary
            print("\nDownload Summary:")
            print(f"Total files: {len(files_to_download)}")
            print(f"Successfully downloaded: {len(files_to_download) - len(failed_files)}")
            print(f"Failed: {len(failed_files)}")
            
            if failed_files:
                print("\nFailed files:")
                for file in failed_files[:10]:  # Show first 10
                    print(f"- {file}")
                if len(failed_files) > 10:
                    print(f"... and {len(failed_files) - 10} more")
            
            return len(failed_files) == 0
            
        except HttpError as e:
            print(f"Google Drive API error: {e}")
            return False
        except Exception as e:
            print(f"Error downloading backup: {e}")
            return False
    
    def _get_files_recursive(self, folder_id, folder_path, files_list):
        """Recursively get all files in a folder and its subfolders"""
        query = f"'{folder_id}' in parents and trashed=false"
        response = self.drive_service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name, mimeType, size)'
        ).execute()
        
        # Process response
        files = response.get('files', [])
        folders = [f for f in files if f['mimeType'] == 'application/vnd.google-apps.folder']
        direct_files = [f for f in files if f['mimeType'] != 'application/vnd.google-apps.folder']
        
        # Add direct files to download list
        for file in direct_files:
            files_list.append({
                'id': file['id'],
                'name': file['name'],
                'size': int(file.get('size', 0)),
                'path': f"{folder_path}/{file['name']}"
            })
        
        # Recursively process subfolders
        for folder in folders:
            subfolder_path = f"{folder_path}/{folder['name']}"
            self._get_files_recursive(folder['id'], subfolder_path, files_list)


class S3Backup(CloudBackupService):
    """AWS S3 backup service"""
    
    def __init__(self, config_dir=None, region_name=None):
        super().__init__(config_dir)
        self.region_name = region_name or 'us-east-1'
        self.config_file = self.config_dir / "s3_config.json"
        self.s3_client = None
        self.bucket_name = None
        
        # Load credentials if exists
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    self.access_key = config.get('access_key')
                    self.secret_key = config.get('secret_key')
                    self.bucket_name = config.get('bucket_name')
                    
                    if self.access_key and self.secret_key:
                        # Initialize S3 client
                        self.s3_client = boto3.client(
                            's3',
                            aws_access_key_id=self.access_key,
                            aws_secret_access_key=self.secret_key,
                            region_name=self.region_name
                        )
                        self.is_authenticated = True
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Error loading S3 config: {e}")
    
    def authenticate(self):
        """Authenticate with AWS S3"""
        print("AWS S3 Authentication")
        print("---------------------")
        access_key = input("Enter AWS Access Key ID: ").strip()
        secret_key = input("Enter AWS Secret Access Key: ").strip()
        bucket_name = input("Enter S3 Bucket Name: ").strip()
        
        try:
            # Initialize S3 client
            s3_client = boto3.client(
                's3',
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region_name=self.region_name
            )
            
            # Test connection by listing buckets
            response = s3_client.list_buckets()
            
            # Check if bucket exists
            bucket_exists = False
            for bucket in response['Buckets']:
                if bucket['Name'] == bucket_name:
                    bucket_exists = True
                    break
            
            if not bucket_exists:
                create_bucket = input(f"Bucket '{bucket_name}' doesn't exist. Create it? (y/n): ").lower() == 'y'
                if create_bucket:
                    # Create bucket
                    if self.region_name == 'us-east-1':
                        s3_client.create_bucket(Bucket=bucket_name)
                    else:
                        s3_client.create_bucket(
                            Bucket=bucket_name,
                            CreateBucketConfiguration={'LocationConstraint': self.region_name}
                        )
                    print(f"Created bucket: {bucket_name}")
                else:
                    print("Authentication failed: Bucket not found")
                    return False
            
            # Save credentials
            config = {
                'access_key': access_key,
                'secret_key': secret_key,
                'bucket_name': bucket_name,
                'region_name': self.region_name
            }
            
            with open(self.config_file, 'w') as f:
                json.dump(config, f)
            
            # Set instance variables
            self.access_key = access_key
            self.secret_key = secret_key
            self.bucket_name = bucket_name
            self.s3_client = s3_client
            self.is_authenticated = True
            
            print("Successfully authenticated with AWS S3!")
            return True
            
        except ClientError as e:
            print(f"AWS S3 error: {e}")
            return False
        except Exception as e:
            print(f"Error authenticating with AWS S3: {e}")
            return False
    
    def upload_file(self, file_path, object_key=None):
        """Upload a single file to S3"""
        if not self.is_authenticated:
            print("Not authenticated. Call authenticate() first.")
            return False
        
        file_path = Path(file_path)
        if not file_path.exists():
            print(f"File not found: {file_path}")
            return False
        
        # If object key not specified, use filename
        if object_key is None:
            object_key = f"Photo_Organizer_Backup/{file_path.name}"
        
        try:
            print(f"Uploading {file_path} to S3...")
            
            # Upload file
            self.s3_client.upload_file(
                str(file_path),
                self.bucket_name,
                object_key
            )
            
            print(f"Successfully uploaded {file_path} to S3")
            return True
            
        except ClientError as e:
            print(f"AWS S3 error: {e}")
            return False
        except Exception as e:
            print(f"Error uploading file to S3: {e}")
            return False
    
    def upload_directory(self, local_dir, prefix=None, progress_callback=None):
        """Upload a directory to S3"""
        if not self.is_authenticated:
            print("Not authenticated. Call authenticate() first.")
            return False
        
        local_dir = Path(local_dir)
        if not local_dir.exists():
            print(f"Directory not found: {local_dir}")
            return False
        
        # If prefix not specified, create one with timestamp
        if prefix is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            prefix = f"Photo_Organizer_Backup/{local_dir.name}_{timestamp}/"
        
        # Ensure prefix ends with /
        if not prefix.endswith('/'):
            prefix += '/'
        
        # Get list of files to upload
        files_to_upload = []
        total_size = 0
        
        for file_path in local_dir.rglob('*'):
            if file_path.is_file():
                # Calculate relative path for S3
                rel_path = file_path.relative_to(local_dir)
                object_key = f"{prefix}{rel_path}"
                
                # Add file to upload list
                file_size = file_path.stat().st_size
                files_to_upload.append({
                    'path': file_path,
                    'key': object_key,
                    'size': file_size
                })
                total_size += file_size
        
        if not files_to_upload:
            print(f"No files found in {local_dir}")
            return False
        
        print(f"Found {len(files_to_upload)} files to upload ({humanize.naturalsize(total_size)})")
        
        # Create progress bar if no callback provided
        if progress_callback is None:
            progress = tqdm(total=total_size, unit='B', unit_scale=True)
        
        # Upload files
        uploaded_size = 0
        failed_files = []
        
        for file_info in files_to_upload:
            try:
                # Upload file with progress tracking
                if progress_callback:
                    # Use boto3's callback to track progress
                    s3_transfer = boto3.s3.transfer.S3Transfer(
                        self.s3_client,
                        boto3.s3.transfer.TransferConfig(
                            use_threads=True,
                            max_concurrency=10
                        )
                    )
                    s3_transfer.upload_file(
                        str(file_info['path']),
                        self.bucket_name,
                        file_info['key'],
                        callback=lambda bytes_transferred: progress_callback(
                            uploaded_size + bytes_transferred,
                            total_size
                        )
                    )
                else:
                    # Standard upload with local progress tracking
                    self.s3_client.upload_file(
                        str(file_info['path']),
                        self.bucket_name,
                        file_info['key']
                    )
                    # Update progress
                    progress.update(file_info['size'])
                
                uploaded_size += file_info['size']
                
            except Exception as e:
                print(f"\nError uploading {file_info['path']}: {e}")
                failed_files.append(file_info['path'])
        
        # Close progress bar if we created it
        if progress_callback is None:
            progress.close()
        
        # Print summary
        print("\nUpload Summary:")
        print(f"Total files: {len(files_to_upload)}")
        print(f"Successfully uploaded: {len(files_to_upload) - len(failed_files)}")
        print(f"Failed: {len(failed_files)}")
        
        if failed_files:
            print("\nFailed files:")
            for file in failed_files[:10]:  # Show first 10
                print(f"- {file}")
            if len(failed_files) > 10:
                print(f"... and {len(failed_files) - 10} more")
        
        # Create a metadata file for this backup
        metadata = {
            'created': datetime.now().isoformat(),
            'file_count': len(files_to_upload),
            'total_size': total_size,
            'source_directory': str(local_dir)
        }
        
        try:
            metadata_key = f"{prefix}_metadata.json"
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=metadata_key,
                Body=json.dumps(metadata, indent=2)
            )
        except Exception as e:
            print(f"Warning: Could not save backup metadata: {e}")
        
        return len(failed_files) == 0
    
    def list_backups(self):
        """List available backups in S3"""
        if not self.is_authenticated:
            print("Not authenticated. Call authenticate() first.")
            return []
        
        try:
            # List objects with the backup prefix
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix='Photo_Organizer_Backup/',
                Delimiter='/'
            )
            
            backups = []
            
            # Process common prefixes (folders)
            for prefix in response.get('CommonPrefixes', []):
                prefix_name = prefix['Prefix']
                
                # Get metadata if available
                try:
                    metadata_key = f"{prefix_name}_metadata.json"
                    metadata_response = self.s3_client.get_object(
                        Bucket=self.bucket_name,
                        Key=metadata_key
                    )
                    metadata = json.loads(metadata_response['Body'].read().decode('utf-8'))
                    
                    backups.append({
                        'id': prefix_name,
                        'name': prefix_name.split('/')[-2],  # Extract folder name
                        'created': metadata.get('created', 'Unknown'),
                        'file_count': metadata.get('file_count', 'Unknown'),
                        'total_size': metadata.get('total_size', 'Unknown')
                    })
                except:
                    # If metadata not available, add basic info
                    backups.append({
                        'id': prefix_name,
                        'name': prefix_name.split('/')[-2],  # Extract folder name
                        'created': 'Unknown',
                        'file_count': 'Unknown',
                        'total_size': 'Unknown'
                    })
            
            return backups
            
        except ClientError as e:
            print(f"AWS S3 error: {e}")
            return []
        except Exception as e:
            print(f"Error listing backups: {e}")
            return []
    
    def download_backup(self, backup_prefix, destination_dir, progress_callback=None):
        """Download a backup from S3"""
        if not self.is_authenticated:
            print("Not authenticated. Call authenticate() first.")
            return False
        
        destination_dir = Path(destination_dir)
        destination_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # List all objects in the backup prefix
            files_to_download = []
            paginator = self.s3_client.get_paginator('list_objects_v2')
            
            # Ensure prefix ends with /
            if not backup_prefix.endswith('/'):
                backup_prefix += '/'
            
            # Skip metadata file when downloading
            metadata_file = f"{backup_prefix}_metadata.json"
            
            for page in paginator.paginate(Bucket=self.bucket_name, Prefix=backup_prefix):
                for obj in page.get('Contents', []):
                    if obj['Key'] == metadata_file:
                        continue  # Skip metadata file
                        
                    files_to_download.append({
                        'key': obj['Key'],
                        'size': obj['Size']
                    })
            
            if not files_to_download:
                print(f"No files found in backup {backup_prefix}")
                return False
            
            # Calculate total size
            total_size = sum(file['size'] for file in files_to_download)
            print(f"Found {len(files_to_download)} files to download ({humanize.naturalsize(total_size)})")
            
            # Create progress bar if no callback provided
            if progress_callback is None:
                progress = tqdm(total=total_size, unit='B', unit_scale=True)
            
            # Download files
            downloaded_size = 0
            failed_files = []
            
            for file_info in files_to_download:
                try:
                    # Calculate local path
                    rel_path = file_info['key'][len(backup_prefix):]
                    local_path = destination_dir / rel_path
                    
                    # Create parent directory if needed
                    local_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Download file
                    self.s3_client.download_file(
                        self.bucket_name,
                        file_info['key'],
                        str(local_path)
                    )
                    
                    downloaded_size += file_info['size']
                    
                    # Update progress
                    if progress_callback:
                        progress_callback(downloaded_size, total_size)
                    else:
                        progress.update(file_info['size'])
                        
                except Exception as e:
                    print(f"\nError downloading {file_info['key']}: {e}")
                    failed_files.append(file_info['key'])
            
            # Close progress bar if we created it
            if progress_callback is None:
                progress.close()
            
            # Print summary
            print("\nDownload Summary:")
            print(f"Total files: {len(files_to_download)}")
            print(f"Successfully downloaded: {len(files_to_download) - len(failed_files)}")
            print(f"Failed: {len(failed_files)}")
            
            if failed_files:
                print("\nFailed files:")
                for file in failed_files[:10]:  # Show first 10
                    print(f"- {file}")
                if len(failed_files) > 10:
                    print(f"... and {len(failed_files) - 10} more")
            
            return len(failed_files) == 0
            
        except ClientError as e:
            print(f"AWS S3 error: {e}")
            return False
        except Exception as e:
            print(f"Error downloading backup: {e}")
            return False


# Factory function to get appropriate backup service
def get_backup_service(service_type, config_dir=None, **kwargs):
    """
    Factory function to create a backup service instance
    
    Args:
        service_type (str): Type of backup service ('dropbox', 'gdrive', 's3')
        config_dir (Path): Path to configuration directory
        **kwargs: Additional arguments for specific services
    
    Returns:
        CloudBackupService: An instance of the requested backup service
    """
    service_type = service_type.lower()
    
    if service_type == 'dropbox':
        return DropboxBackup(config_dir, **kwargs)
    elif service_type in ('gdrive', 'google', 'googledrive'):
        return GoogleDriveBackup(config_dir, **kwargs)
    elif service_type in ('s3', 'aws', 'awss3'):
        return S3Backup(config_dir, **kwargs)
    else:
        raise ValueError(f"Unsupported backup service: {service_type}")


# Command-line interface
def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Cloud Backup Tool for Photo Organizer')
    parser.add_argument('--service', type=str, required=True, choices=['dropbox', 'gdrive', 's3'],
                        help='Cloud service to use (dropbox, gdrive, s3)')
    parser.add_argument('--action', type=str, required=True, 
                        choices=['auth', 'backup', 'list', 'restore'],
                        help='Action to perform')
    parser.add_argument('--source', type=str, 
                        help='Source directory for backup')
    parser.add_argument('--dest', type=str, 
                        help='Destination directory for restore')
    parser.add_argument('--backup-id', type=str, 
                        help='Backup ID/path for restore operation')
    
    args = parser.parse_args()
    
    # Get backup service
    try:
        service = get_backup_service(args.service)
    except ValueError as e:
        print(f"Error: {e}")
        return
    
    # Perform action
    if args.action == 'auth':
        # Authenticate
        success = service.authenticate()
        if success:
            print(f"Successfully authenticated with {args.service}")
        else:
            print(f"Failed to authenticate with {args.service}")
    
    elif args.action == 'backup':
        # Verify source directory
        if not args.source:
            print("Error: Source directory required for backup")
            return
        
        source_dir = Path(args.source)
        if not source_dir.exists():
            print(f"Error: Source directory not found: {source_dir}")
            return
        
        # Authenticate if needed
        if not service.is_authenticated:
            print("Not authenticated. Authenticating...")
            success = service.authenticate()
            if not success:
                print("Authentication failed. Aborting.")
                return
        
        # Perform backup
        success = service.upload_directory(source_dir)
        if success:
            print(f"Backup completed successfully")
        else:
            print(f"Backup completed with errors")
    
    elif args.action == 'list':
        # Authenticate if needed
        if not service.is_authenticated:
            print("Not authenticated. Authenticating...")
            success = service.authenticate()
            if not success:
                print("Authentication failed. Aborting.")
                return
        
        # List backups
        backups = service.list_backups()
        
        if not backups:
            print("No backups found")
            return
        
        print(f"Found {len(backups)} backups:")
        for i, backup in enumerate(backups, 1):
            created = backup.get('created', 'Unknown')
            if 'total_size' in backup and backup['total_size'] != 'Unknown':
                size = humanize.naturalsize(backup['total_size'])
            else:
                size = 'Unknown size'
                
            print(f"{i}. {backup['name']} - {created} ({size})")
            print(f"   ID: {backup['id']}")
            print()
    
    elif args.action == 'restore':
        # Verify destination directory and backup ID
        if not args.dest:
            print("Error: Destination directory required for restore")
            return
        
        if not args.backup_id:
            print("Error: Backup ID required for restore")
            return
        
        dest_dir = Path(args.dest)
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        # Authenticate if needed
        if not service.is_authenticated:
            print("Not authenticated. Authenticating...")
            success = service.authenticate()
            if not success:
                print("Authentication failed. Aborting.")
                return
        
        # Perform restore
        success = service.download_backup(args.backup_id, dest_dir)
        if success:
            print(f"Restore completed successfully")
        else:
            print(f"Restore completed with errors")


if __name__ == "__main__":
    main()