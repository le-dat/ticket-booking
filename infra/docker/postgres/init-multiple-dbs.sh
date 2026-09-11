set -e
set -u

echo "========================================================="
echo "   Đang khởi tạo các Microservice Databases cô lập...   "
echo "========================================================="

# Danh sách: Tên DB : Tên User : Mật khẩu User
DATABASES_CONFIG=(
    "auth_db:auth_user:${AUTH_DB_PASSWORD:-auth_pass_secret_123}"
    "product_db:product_user:${PRODUCT_DB_PASSWORD:-product_pass_secret_123}"
    "order_db:order_user:${ORDER_DB_PASSWORD:-order_pass_secret_123}"
    "payment_db:payment_user:${PAYMENT_DB_PASSWORD:-payment_pass_secret_123}"
)

for entry in "${DATABASES_CONFIG[@]}"; do
    IFS=":" read -r DB_NAME DB_USER DB_PASS <<< "$entry"
    echo "--> Tạo: Database='$DB_NAME' với Owner='$DB_USER'..."

    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
        -- 1. Tạo User riêng biệt nếu chưa có
        DO \$\$
        BEGIN
            IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '$DB_USER') THEN
                CREATE USER $DB_USER WITH ENCRYPTED PASSWORD '$DB_PASS';
            END IF;
        END
        \$\$;

        -- 2. Tạo Database gán quyền Owner cho User đó
        SELECT 'CREATE DATABASE $DB_NAME OWNER $DB_USER'
        WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$DB_NAME')\gexec

        -- 3. Tước bỏ toàn bộ quyền mặc định của các user khác
        REVOKE ALL ON DATABASE $DB_NAME FROM PUBLIC;

        -- 4. Cấp toàn quyền cho chính chủ sở hữu
        GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
EOSQL

    echo "    [OK] Đã cấu hình xong $DB_NAME"
done

echo "========================================================="
echo "   Đã khởi tạo xong 4 Database với quyền cô lập 100%!   "
echo "========================================================="