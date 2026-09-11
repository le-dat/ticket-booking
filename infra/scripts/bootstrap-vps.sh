set -euo pipefail

NODE_ROLE="${1:-data}" # 'data' (VPS 2) hoặc 'app' (VPS 1)
PEER_IP="${2:-}"       # IP của VPS còn lại để mở firewall

echo "========================================================="
echo "   Khởi tạo VPS cho E-Commerce Platform (Vai trò: $NODE_ROLE)"
echo "========================================================="

echo "--- [1] Cập nhật OS & Cài đặt công cụ nền tảng ---"
sudo apt-get update -y
sudo apt-get install -y curl wget git jq htop ufw fail2ban ca-certificates gnupg lsb-release

echo "--- [2] Thiết lập 4GB Swap ---"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
bash "$SCRIPT_DIR/setup-swap.sh"

echo "--- [3] Tối ưu giới hạn Kernel cho Kafka ---"
sudo sysctl -w vm.max_map_count=262144
sudo sysctl -w fs.file-max=65536
if ! grep -q "vm.max_map_count" /etc/sysctl.conf; then
    echo "vm.max_map_count=262144" | sudo tee -a /etc/sysctl.conf
fi
if ! grep -q "fs.file-max" /etc/sysctl.conf; then
    echo "fs.file-max=65536" | sudo tee -a /etc/sysctl.conf
fi

echo "--- [4] Cài đặt Docker Engine & Docker Compose Plugin ---"
if ! command -v docker &> /dev/null; then
    sudo install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o
/etc/apt/keyrings/docker.gpg --yes
    sudo chmod a+r /etc/apt/keyrings/docker.gpg

    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg]
https://download.docker.com/linux/ubuntu \
      $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
      sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

    sudo apt-get update -y
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin
docker-compose-plugin
    sudo usermod -aG docker "$USER" || true
fi

echo "--- [5] Cấu hình tường lửa UFW ---"
sudo ufw --force default deny incoming
sudo ufw --force default allow outgoing
sudo ufw allow 22/tcp comment "SSH"

if [ "$NODE_ROLE" == "app" ]; then
    sudo ufw allow 80/tcp comment "HTTP"
    sudo ufw allow 443/tcp comment "HTTPS"
    sudo ufw allow 8000/tcp comment "Kong Proxy"
elif [ "$NODE_ROLE" == "data" ]; then
    if [ -n "$PEER_IP" ]; then
        echo "Mở cổng Postgres (5432), Kafka (9092), Redis (6379) cho riêng IP VPS 1:
$PEER_IP"
        sudo ufw allow from "$PEER_IP" to any port 5432 proto tcp comment "Postgres từ App
Node"
        sudo ufw allow from "$PEER_IP" to any port 9092 proto tcp comment "Kafka từ App Node"
        sudo ufw allow from "$PEER_IP" to any port 6379 proto tcp comment "Redis từ App Node"
    fi
fi

sudo ufw --force enable
sudo ufw status verbose