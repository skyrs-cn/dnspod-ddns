#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import time
import socket
from typing import Optional, Tuple, List, Callable

import requests
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.dnspod.v20210323 import dnspod_client, models


# ========= 从环境变量读取配置 =========
SECRET_ID = os.getenv("TENCENTCLOUD_SECRET_ID", "").strip()
SECRET_KEY = os.getenv("TENCENTCLOUD_SECRET_KEY", "").strip()

# 多域名支持（逗号分隔）
DDNS_DOMAINS = os.getenv("DDNS_DOMAINS", "").strip()
# 兼容单域名配置
DDNS_DOMAIN_SINGLE = os.getenv("DDNS_DOMAIN", "").strip()

ENABLE_IPV4 = os.getenv("DDNS_ENABLE_IPV4", "true").lower() == "true"
ENABLE_IPV6 = os.getenv("DDNS_ENABLE_IPV6", "true").lower() == "true"

TTL = int(os.getenv("DDNS_TTL", "600"))
INTERVAL = int(os.getenv("DDNS_INTERVAL", "3600"))  # 秒

# 多个公网 IPv4 接口
IPV4_APIS: List[str] = [
    "https://api.ipify.org",
    "https://ipv4.icanhazip.com",
    "https://v4.ident.me",
    "https://ip.3322.net",
]

# 多个公网 IPv6 接口
IPV6_APIS: List[str] = [
    "https://api64.ipify.org",
    "https://ipv6.icanhazip.com",
    "https://v6.ident.me",
]


def log(msg: str):
    """简单日志输出"""
    print(msg, flush=True)


# ========= 获取公网 IP 工具 =========
def _validate_ipv4(ip: str) -> bool:
    try:
        socket.inet_pton(socket.AF_INET, ip)
        return True
    except OSError:
        return False


def _validate_ipv6(ip: str) -> bool:
    try:
        socket.inet_pton(socket.AF_INET6, ip)
        return True
    except OSError:
        return False


def get_ip_from_apis(apis: List[str], validate_func: Callable[[str], bool], desc: str) -> str:
    """
    依次尝试多个接口获取 IP
    """
    last_err = None
    for api in apis:
        try:
            r = requests.get(api, timeout=8)
            r.raise_for_status()
            ip = r.text.strip()
            if validate_func(ip):
                log(f"[IP] {desc} 获取成功: {ip} (via {api})")
                return ip
            else:
                log(f"[IP] {desc} 从 {api} 获取到的 IP 格式不正确: {ip}")
        except Exception as e:
            last_err = e
            log(f"[IP] {desc} 从 {api} 获取失败: {e}")
    log(f"[IP] 所有 {desc} 接口均尝试失败")
    if last_err:
        raise last_err
    raise RuntimeError(f"无法获取 {desc} 地址")


def get_public_ipv4() -> str:
    return get_ip_from_apis(IPV4_APIS, _validate_ipv4, "IPv4")


def get_public_ipv6() -> str:
    return get_ip_from_apis(IPV6_APIS, _validate_ipv6, "IPv6")


# ========= DNSPod 客户端与操作 =========
def get_dnspod_client():
    if not SECRET_ID or not SECRET_KEY:
        log("ERROR: TENCENTCLOUD_SECRET_ID / TENCENTCLOUD_SECRET_KEY 未配置")
        sys.exit(1)
    cred = credential.Credential(SECRET_ID, SECRET_KEY)
    client = dnspod_client.DnspodClient(cred, "")
    return client


def split_domain(full_domain: str) -> Tuple[str, str]:
    """
    将 full_domain 拆成 (subdomain, domain)
    如:
        home.example.com -> ("home", "example.com")
        example.com      -> ("@",   "example.com")
    """
    parts = [p for p in full_domain.split(".") if p]  # 过滤空串，避免末尾有点
    if len(parts) < 2:
        raise ValueError(f"DDNS_DOMAIN 格式不正确: {full_domain}")
    domain = ".".join(parts[-2:])
    if len(parts) == 2:
        subdomain = "@"
    else:
        subdomain = ".".join(parts[:-2])
    return subdomain, domain


def find_record(
    client,
    domain: str,
    subdomain: str,
    record_type: str,
) -> Tuple[Optional[int], Optional[str]]:
    """
    查询解析记录，返回第一条匹配记录
    """
    req = models.DescribeRecordListRequest()
    params = {
        "Domain": domain,
        "Subdomain": subdomain,
        "RecordType": record_type,
    }
    req.from_json_string(json.dumps(params))
    try:
        resp = client.DescribeRecordList(req)
        records = resp.RecordList or []
        for record in records:
            if record.Name == subdomain and record.Type == record_type:
                return record.RecordId, record.Value
        return None, None
    except TencentCloudSDKException as e:
        log(f"[DNSPod] 查询记录失败: {e}")
        raise


def create_record(
    client,
    domain: str,
    subdomain: str,
    record_type: str,
    value: str,
) -> int:
    req = models.CreateRecordRequest()
    params = {
        "Domain": domain,
        "SubDomain": subdomain,
        "RecordType": record_type,
        "RecordLine": "默认",
        "Value": value,
        "TTL": TTL,
    }
    req.from_json_string(json.dumps(params))
    try:
        resp = client.CreateRecord(req)
        log(f"[DNSPod] 创建记录: {subdomain}.{domain} {record_type} -> {value}, RecordId={resp.RecordId}")
        return resp.RecordId
    except TencentCloudSDKException as e:
        log(f"[DNSPod] 创建记录失败: {e}")
        raise


def update_record(
    client,
    domain: str,
    record_id: int,
    subdomain: str,
    record_type: str,
    value: str,
):
    req = models.ModifyRecordRequest()
    params = {
        "Domain": domain,
        "RecordId": record_id,
        "SubDomain": subdomain,
        "RecordType": record_type,
        "RecordLine": "默认",
        "Value": value,
        "TTL": TTL,
    }
    req.from_json_string(json.dumps(params))
    try:
        resp = client.ModifyRecord(req)
        log(f"[DNSPod] 更新记录: {subdomain}.{domain} {record_type} -> {value}, RecordId={record_id}")
        return resp.RecordId
    except TencentCloudSDKException as e:
        log(f"[DNSPod] 更新记录失败: {e}")
        raise


# ========= 一次 DDNS 操作（单个域名） =========
def ddns_for_one_domain(client, full_domain: str, ipv4: Optional[str], ipv6: Optional[str]):
    """
    对单个 full_domain 执行一次 DDNS 更新
    ipv4 / ipv6 可提前获取好传进来，减少重复调用 IP 接口
    """
    try:
        subdomain, domain = split_domain(full_domain)
    except ValueError as e:
        log(f"[DDNS] 域名格式错误: {e}")
        return

    log(f"[DDNS] 开始更新 {full_domain}，subdomain={subdomain}, domain={domain}")

    if ENABLE_IPV4 and ipv4:
        try:
            record_id, current = find_record(client, domain, subdomain, "A")
            if record_id is None:
                log(f"[DDNS][IPv4] 未发现 A 记录，将创建 {full_domain} -> {ipv4}")
                create_record(client, domain, subdomain, "A", ipv4)
            else:
                if current == ipv4:
                    log(f"[DDNS][IPv4] A 记录已是 {ipv4}，无需更新")
                else:
                    log(f"[DDNS][IPv4] A 记录当前 {current}，将更新为 {ipv4}")
                    update_record(client, domain, record_id, subdomain, "A", ipv4)
        except Exception as e:
            log(f"[DDNS][IPv4] 更新 {full_domain} 失败: {e}")

    if ENABLE_IPV6 and ipv6:
        try:
            record_id, current = find_record(client, domain, subdomain, "AAAA")
            if record_id is None:
                log(f"[DDNS][IPv6] 未发现 AAAA 记录，将创建 {full_domain} -> {ipv6}")
                create_record(client, domain, subdomain, "AAAA", ipv6)
            else:
                if current == ipv6:
                    log(f"[DDNS][IPv6] AAAA 记录已是 {ipv6}，无需更新")
                else:
                    log(f"[DDNS][IPv6] AAAA 记录当前 {current}，将更新为 {ipv6}")
                    update_record(client, domain, record_id, subdomain, "AAAA", ipv6)
        except Exception as e:
            log(f"[DDNS][IPv6] 更新 {full_domain} 失败: {e}")

    log(f"[DDNS] {full_domain} 更新结束")


# ========= 一轮 DDNS，处理所有域名 =========
def ddns_once():
    # 解析域名列表
    domains: List[str] = []
    if DDNS_DOMAINS:
        domains = [d.strip() for d in DDNS_DOMAINS.split(",") if d.strip()]
    elif DDNS_DOMAIN_SINGLE:
        domains = [DDNS_DOMAIN_SINGLE]
    else:
        log("ERROR: 请配置 DDNS_DOMAINS 或 DDNS_DOMAIN")
        return

    if not domains:
        log("ERROR: 域名列表为空")
        return

    if not (ENABLE_IPV4 or ENABLE_IPV6):
        log("WARN: IPv4 和 IPv6 都未启用，什么都不会做")
        return

    client = get_dnspod_client()

    # 为了减少对公共 IP 接口的压力，一轮中 IPv4/IPv6 只获取一次
    ipv4 = None
    ipv6 = None

    if ENABLE_IPV4:
        try:
            ipv4 = get_public_ipv4()
        except Exception as e:
            log(f"[DDNS][IPv4] 获取公网 IPv4 失败，本轮所有域名的 IPv4 更新将跳过: {e}")

    if ENABLE_IPV6:
        try:
            ipv6 = get_public_ipv6()
        except Exception as e:
            log(f"[DDNS][IPv6] 获取公网 IPv6 失败，本轮所有域名的 IPv6 更新将跳过: {e}")

    if (ENABLE_IPV4 and not ipv4) and (ENABLE_IPV6 and not ipv6):
        log("[DDNS] 本轮无法获取任一 IP，放弃更新")
        return

    log(f"[DDNS] 本轮更新域名列表: {', '.join(domains)}")
    for d in domains:
        ddns_for_one_domain(client, d, ipv4, ipv6)


def main_loop():
    domains_display = DDNS_DOMAINS if DDNS_DOMAINS else DDNS_DOMAIN_SINGLE
    log(f"[Service] DNSPod DDNS 服务启动，间隔 {INTERVAL} 秒")
    log(f"[Service] 目标域名: {domains_display}")
    log(f"[Service] IPv4: {ENABLE_IPV4}, IPv6: {ENABLE_IPV6}, TTL={TTL}")

    ddns_once()
    while True:
        time.sleep(INTERVAL)
        ddns_once()


if __name__ == "__main__":
    main_loop()