FROM python:3.11-slim

# 安装运行依赖
RUN pip install --no-cache-dir tencentcloud-sdk-python requests

WORKDIR /app

# 拷贝脚本
COPY ddns_dnspod.py /app/ddns_dnspod.py

# 设置时区（按需，可选）
# RUN ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && echo "Asia/Shanghai" > /etc/timezone

CMD ["python", "/app/ddns_dnspod.py"]