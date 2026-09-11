set -euo pipefail

SWAP_SIZE="4G"
SWAP_FILE="/swapfile"

echo "=== [1/5] Kiểm tra Swap hiện tại ==="
if swapon --show | grep -q "$SWAP_FILE"; then
    echo "Swapfile $SWAP_FILE đã tồn tại và đang hoạt động. Bỏ qua."
    exit 0
fi

echo "=== [2/5] Tạo file swap dung lượng $SWAP_SIZE tại $SWAP_FILE ==="
sudo fallocate -l "$SWAP_SIZE" "$SWAP_FILE" || sudo dd if=/dev/zero of="$SWAP_FILE" bs=1G
count=4 status=progress

echo "=== [3/5] Phân quyền an toàn (chmod 600) ==="
sudo chmod 600 "$SWAP_FILE"

echo "=== [4/5] Định dạng và kích hoạt Swap ==="
sudo mkswap "$SWAP_FILE"
sudo swapon "$SWAP_FILE"

echo "=== [5/5] Cấu hình tự kích hoạt khi khởi động lại & thiết lập swappiness=10 ==="
if ! grep -q "$SWAP_FILE" /etc/fstab; then
    echo "$SWAP_FILE none swap sw 0 0" | sudo tee -a /etc/fstab
fi

sudo sysctl vm.swappiness=10
if ! grep -q "vm.swappiness" /etc/sysctl.conf; then
    echo "vm.swappiness=10" | sudo tee -a /etc/sysctl.conf
else
    sudo sed -i 's/vm.swappiness=.*/vm.swappiness=10/' /etc/sysctl.conf
fi

echo "=== Swap đã thiết lập thành công! ==="
free -h