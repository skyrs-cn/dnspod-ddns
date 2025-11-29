# DNSPod DDNS (Docker 版)

一个基于腾讯云 DNSPod API 的 DDNS 脚本，支持：

- IPv4 / IPv6
- 多个域名（逗号分隔）
- 多个公网 IP 查询接口（防止单个接口不可用）
- 通过环境变量或 `.env` 文件配置
- 容器内定时循环执行（默认每小时）
- 支持 Docker / Docker Compose 一键部署

适合部署在内网服务器 / NAS 上，通过 Docker 长期运行。

---

## 一、前置准备

1. **域名托管在 DNSPod / 腾讯云解析**

   在「域名解析」控制台中能看到你的域名（例如 `example.com`）。

2. **获取腾讯云 API 密钥**

   - 登录 [腾讯云控制台](https://console.cloud.tencent.com/)
   - 「访问管理」->「访问密钥」->「API 密钥管理」
   - 创建密钥，获得：
     - `SecretId`
     - `SecretKey`

> 密钥请妥善保管，不要上传到公开仓库。

---

## 二、项目结构

示例仓库结构如下：

```text
dnspod-ddns/
├─ ddns_dnspod.py
├─ Dockerfile
├─ docker-compose.yml
└─ README.md
```

---

## 三、环境变量说明

支持多域名 / 单域名两种配置方式，通过环境变量（或 `.env` 文件）传入。

### 1. 腾讯云密钥（必需）

```bash
TENCENTCLOUD_SECRET_ID=你的SecretId
TENCENTCLOUD_SECRET_KEY=你的SecretKey
```

### 2. 域名配置

**多域名（推荐）**：逗号分隔多个完整域名

```bash
DDNS_DOMAINS=home.example.com,nas.example.com,example.com
```

**单域名（兼容旧方式）**：

```bash
DDNS_DOMAIN=home.example.com
```

> 说明：
> - `DDNS_DOMAINS` 和 `DDNS_DOMAIN` 至少配置一个；
> - 如果同时配置了 `DDNS_DOMAINS` 和 `DDNS_DOMAIN`，脚本优先使用 `DDNS_DOMAINS`；
> - 完整域名示例：`home.example.com`，`nas.example.com`，`example.com` 等。

### 3. 网络类型开关

```bash
# 是否启用 IPv4 / IPv6（不区分大小写，"true"/"false"）
DDNS_ENABLE_IPV4=true
DDNS_ENABLE_IPV6=true
```

> 如果你的网络没有 IPv6 出口，请将 `DDNS_ENABLE_IPV6` 设为 `false`，避免无意义的 IPv6 失败日志。

### 4. 其他参数

```bash
# 解析记录 TTL（秒），默认 600
DDNS_TTL=600

# 检查/更新间隔（秒），默认 3600（1 小时）
DDNS_INTERVAL=3600
```

---

## 四、使用 Docker 手动构建/运行

### 0. 直接拉取已构建镜像（推荐）

仓库已将多架构镜像推送至 `ghcr.io/skyrs-cn/dnspod-ddns`。镜像标签格式为 `架构_时间戳`，例如 `arm_20251129142310`，可根据需要选择对应架构：

```bash
# 查看最新标签（可在 GitHub Packages 或 ghcr.io 页面查看）
# 假设需要拉取 amd64 架构 2025-11-29 的构建：
docker pull ghcr.io/skyrs-cn/dnspod-ddns:amd_20251129142310

# ARM 版本示例
docker pull ghcr.io/skyrs-cn/dnspod-ddns:arm_20251129142310
```

拉取后即可按照下文的 `docker run` 或 `docker compose` 示例，将镜像名称替换为 `ghcr.io/skyrs-cn/dnspod-ddns:<tag>`。

### 1. 构建镜像

在项目根目录（包含 `Dockerfile` 的目录）执行：

```bash
docker build -t dnspod-ddns:latest .
```

### 2. 直接用 docker run 启动

#### 示例 1：多域名 + IPv4/IPv6

```bash
docker run -d \
  --name dnspod-ddns \
  -e TENCENTCLOUD_SECRET_ID="你的SecretId" \
  -e TENCENTCLOUD_SECRET_KEY="你的SecretKey" \
  -e DDNS_DOMAINS="home.example.com,nas.example.com" \
  -e DDNS_ENABLE_IPV4="true" \
  -e DDNS_ENABLE_IPV6="true" \
  -e DDNS_TTL="600" \
  -e DDNS_INTERVAL="3600" \
  dnspod-ddns:latest
```

#### 示例 2：只更新 IPv4，单域名

```bash
docker run -d \
  --name dnspod-ddns \
  -e TENCENTCLOUD_SECRET_ID="你的SecretId" \
  -e TENCENTCLOUD_SECRET_KEY="你的SecretKey" \
  -e DDNS_DOMAIN="home.example.com" \
  -e DDNS_ENABLE_IPV4="true" \
  -e DDNS_ENABLE_IPV6="false" \
  dnspod-ddns:latest
```

---

## 五、使用 Docker Compose 一键启动

项目中已经提供了一个 `docker-compose.yml` 示例，内容大致如下：

```yaml
version: "3.8"

services:
  dnspod-ddns:
    build: .
    container_name: dnspod-ddns
    restart: unless-stopped
    environment:
      # ==== 必填：腾讯云 API 密钥 ====
      TENCENTCLOUD_SECRET_ID: "你的SecretId"
      TENCENTCLOUD_SECRET_KEY: "你的SecretKey"

      # ==== 域名配置：推荐使用多域名 ====
      # 多个域名用逗号分隔，例如：
      # DDNS_DOMAINS: "home.example.com,nas.example.com,example.com"
      DDNS_DOMAINS: "home.example.com"

      # 单域名旧配置方式（可选，通常不需要，DDNS_DOMAINS 优先）
      # DDNS_DOMAIN: "home.example.com"

      # ==== IPv4 / IPv6 开关 ====
      DDNS_ENABLE_IPV4: "true"
      DDNS_ENABLE_IPV6: "true"

      # ==== 其他参数 ====
      DDNS_TTL: "600"      # TTL，单位：秒
      DDNS_INTERVAL: "3600" # 更新间隔，单位：秒

    # 如果希望容器时间与宿主机一致，可按需开启（可选）
    # volumes:
    #   - /etc/localtime:/etc/localtime:ro
```

### 1. 使用 compose 启动

在项目根目录执行：

```bash
docker compose up -d
# 或老版本 docker-compose：
# docker-compose up -d
```

### 2. 查看日志

```bash
docker compose logs -f
# 或：docker-compose logs -f
```

容器启动后会：

1. 立即执行一次 DDNS 更新；
2. 然后每隔 `DDNS_INTERVAL` 秒执行一次。

---

## 六、使用 .env 管理敏感信息（推荐）

为避免将密钥写在 `docker-compose.yml` 中，你可以使用 `.env` 文件。

### 1. 创建 `.env` 文件

在项目根目录新建 `.env`：

```env
TENCENTCLOUD_SECRET_ID=你的SecretId
TENCENTCLOUD_SECRET_KEY=你的SecretKey

DDNS_DOMAINS=home.example.com,nas.example.com
# 单域名也可以，仅写一个：
# DDNS_DOMAINS=home.example.com

DDNS_ENABLE_IPV4=true
DDNS_ENABLE_IPV6=true
DDNS_TTL=600
DDNS_INTERVAL=3600
```

### 2. 修改 docker-compose.yml 使用变量

将 `docker-compose.yml` 的 `environment` 部分改为引用 `.env` 中的变量：

```yaml
version: "3.8"

services:
  dnspod-ddns:
    build: .
    container_name: dnspod-ddns
    restart: unless-stopped
    environment:
      TENCENTCLOUD_SECRET_ID: "${TENCENTCLOUD_SECRET_ID}"
      TENCENTCLOUD_SECRET_KEY: "${TENCENTCLOUD_SECRET_KEY}"
      DDNS_DOMAINS: "${DDNS_DOMAINS}"
      DDNS_ENABLE_IPV4: "${DDNS_ENABLE_IPV4}"
      DDNS_ENABLE_IPV6: "${DDNS_ENABLE_IPV6}"
      DDNS_TTL: "${DDNS_TTL}"
      DDNS_INTERVAL: "${DDNS_INTERVAL}"
```

然后直接：

```bash
docker compose up -d
```

Compose 会自动加载当前目录的 `.env` 文件。

---

## 七、工作原理简述

1. 容器启动后，`ddns_dnspod.py` 会：
   - 从多个公网 IP 接口依次尝试获取当前 IPv4/IPv6 地址（例如 `api.ipify.org`、`icanhazip.com` 等）；
   - 解析出每个完整域名对应的主域名和主机记录（如 `home.example.com` -> `example.com` + `home`）；
   - 通过 DNSPod API 查询解析记录：
     - 若记录不存在则创建；
     - 若记录存在且 IP 变化则更新；
     - 若记录存在且 IP 未变化则不操作；
2. 一轮中 IPv4/IPv6 只各获取一次，并复用给所有域名，减少对公网 IP 接口的请求；
3. 脚本在容器中以死循环运行，每隔 `DDNS_INTERVAL` 秒执行一轮。

---

## 八、常见问题

### 1. IPv6 一直获取失败？

- 确认宿主机本身有 IPv6 出口：
  ```bash
  curl https://api64.ipify.org
  ```
- 如果没有 IPv6 出口，请将 `DDNS_ENABLE_IPV6=false`。

### 2. 只想更新根域名（例如 `example.com`）？

- 直接把根域名写入：
  ```bash
  DDNS_DOMAINS=example.com
  # 或单域名:
  # DDNS_DOMAIN=example.com
  ```
- 脚本会自动将其解析为主机记录 `@` + 主域名 `example.com`。

### 3. 想用系统 crontab，而不是容器循环？

- 可以直接在宿主机运行脚本，不用 Docker：
  ```bash
  pip install tencentcloud-sdk-python requests
  ```
- 然后用 crontab 定时执行（示例每 5 分钟）：
  ```bash
  */5 * * * * TENCENTCLOUD_SECRET_ID=xxx TENCENTCLOUD_SECRET_KEY=yyy DDNS_DOMAIN=home.example.com /usr/bin/python3 /path/to/ddns_dnspod.py
  ```

---

## 九、免责声明

本项目示例仅用于个人学习与自建服务，请勿将密钥泄露或上传到公共仓库。  
使用过程中的一切风险由使用者自行承担。
