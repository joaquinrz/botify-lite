#!/bin/bash
# Define function for consistent status messaging with timestamps
echo_status() { local msg=$1; echo "[$(date -u +%Y-%m-%dT%H:%M:%S%Z)] $msg" | tee -a ~/status; }

echo_status "on-create start"
# Install Python development tools
echo_status "Installing Python development tools"
pip install --no-cache-dir ipython ipykernel
pip install "black[jupyter]"

# only run apt upgrade on pre-build
sudo apt-get update
if [ "$CODESPACE_NAME" = "null" ]
then
    echo_status "apt upgrading"
    sudo apt-get upgrade -y
fi

# Additional git setup
echo_status "Setting up git configurations and zsh utilities"
# Setup git aliases
cp .devcontainer/gitconfig-base ~/.gitconfig
# Configure zsh auto-update mode
echo "zstyle ':omz:update' mode auto" >> ~/.zshrc
# Install git diff enhancement tools
echo_status "Installing git diff tools (delta and diff-so-fancy)"
# Install delta - a syntax-highlighting pager for git
wget -q "$(curl -s https://api.github.com/repos/dandavison/delta/releases/latest | jq '.assets[].browser_download_url' -r | grep -vE 'musl|darwin|arm|apple|windows' | grep 'amd64.*deb')" -O /tmp/delta.deb
sudo dpkg -i /tmp/delta.deb

# Install diff-so-fancy - another git diff improvement tool
wget -q "$(curl -s https://api.github.com/repos/so-fancy/diff-so-fancy/releases/latest | jq '.assets[].browser_download_url' -r)" --output-document /tmp/diff-so-fancy
chmod +x /tmp/diff-so-fancy && sudo mv /tmp/diff-so-fancy /usr/local/bin/

# Set zsh as the default shell for the user
echo_status "Setting zsh as default shell"
sudo chsh --shell /bin/zsh "$USER"
echo_status "on-create complete"