# Auth Flow

`AuthManager` (`app/auth/auth_manager.py`) opens a browser to the DKP OAuth page, spins up `CallbackServer` (`app/auth/callback_server.py`) to catch the redirect, exchanges the code for tokens, and stores them in the system keychain via `keyring`.

`ApiClient` (`app/auth/api_client.py`) is the authenticated HTTP client for all REST calls — attach it after auth bootstrap in `main.py`.
