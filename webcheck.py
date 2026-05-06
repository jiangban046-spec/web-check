#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网站监控脚本 - 计划任务优化版
用于解决计划任务环境下日志生成问题
"""

import requests
import configparser
import time
import os
import sys
from datetime import datetime
import logging
import traceback

def get_script_directory():
    """获取脚本所在目录"""
    if getattr(sys, 'frozen', False):
        # 如果是打包后的exe文件
        script_dir = os.path.dirname(sys.executable)
    elif '__file__' in globals():
        # 如果是脚本文件
        script_dir = os.path.dirname(os.path.abspath(__file__))
    else:
        # 如果无法确定脚本路径，使用当前工作目录
        script_dir = os.getcwd()
    return script_dir

def setup_logging():
    """设置日志记录 - 支持计划任务环境"""
    try:
        # 获取脚本所在目录
        script_dir = get_script_directory()
        
        # 尝试在脚本目录创建日志目录
        log_dir = os.path.join(script_dir, 'logs')
        if not os.path.exists(log_dir):
            try:
                os.makedirs(log_dir, exist_ok=True)
            except:
                # 如果在脚本目录创建失败，尝试在临时目录创建
                import tempfile
                log_dir = os.path.join(tempfile.gettempdir(), 'webcheck_logs')
                os.makedirs(log_dir, exist_ok=True)
        
        # 创建按日期的日志文件
        current_date = datetime.now().strftime('%Y-%m-%d')
        log_filename = f"webcheck_{current_date}.log"
        log_filepath = os.path.join(log_dir, log_filename)
        
        # 配置日志格式
        log_format = '%(asctime)s - %(levelname)s - %(message)s'
        
        # 清除现有的日志处理器
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
        
        # 创建新的日志处理器
        file_handler = logging.FileHandler(log_filepath, encoding='utf-8', mode='a')
        console_handler = logging.StreamHandler(sys.stdout)
        
        formatter = logging.Formatter(log_format)
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # 配置日志器
        logging.basicConfig(
            level=logging.INFO,
            handlers=[file_handler, console_handler],
            force=True  # 强制重新配置
        )
        
        return logging.getLogger(), log_filepath
        
    except Exception as e:
        # 如果日志设置失败，至少输出到控制台
        print(f"日志设置失败: {e}")
        logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler(sys.stdout)])
        return logging.getLogger(), ""

def read_config(config_file):
    """读取配置文件"""
    config = configparser.ConfigParser()
    
    if not os.path.exists(config_file):
        return None, f"配置文件 {config_file} 不存在，路径: {os.path.abspath(config_file)}"
    
    try:
        config.read(config_file, encoding='utf-8')
    except Exception as e:
        return None, f"读取配置文件失败: {str(e)}"
    
    required_sections = ['webhook', 'url', 'timeout', 'logfile']
    for section in required_sections:
        if not config.has_section(section):
            return None, f"缺少配置节: [{section}]"
    
    try:
        webhook = config.get('webhook', 'webhook')
        url_file_path = config.get('url', 'url')
        timeout = int(config.get('timeout', 'timeout'))
        log_file_path = config.get('logfile', 'logfile')
    except Exception as e:
        return None, f"读取配置项失败: {str(e)}"
    
    default_template = """【网站监控告警】
时间: {timestamp}
网站: {url}
描述: {description}
状态: {status_code}
结果: 无法访问"""

    return {
        'webhook': webhook,
        'url_file_path': url_file_path,
        'timeout': timeout,
        'message_template': default_template,
        'log_file_path': log_file_path
    }, None

def send_wechat_message(webhook_url, message):
    """发送微信机器人消息"""
    headers = {
        'Content-Type': 'application/json; charset=utf-8'
    }
    
    payload = {
        "msgtype": "text",
        "text": {
            "content": message
        }
    }
    
    try:
        response = requests.post(webhook_url, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            logging.info("微信消息发送成功")
        else:
            logging.error(f"微信消息发送失败，状态码: {response.status_code}, 响应: {response.text}")
    except Exception as e:
        logging.error(f"发送微信消息时发生异常: {e}")

def check_urls(config_data):
    """检查URL列表"""
    if not os.path.exists(config_data['url_file_path']):
        return False, f"URL文件 {config_data['url_file_path']} 不存在，路径: {os.path.abspath(config_data['url_file_path'])}"
    
    try:
        with open(config_data['url_file_path'], 'r', encoding='utf-8') as file:
            lines = file.readlines()
    except Exception as e:
        return False, f"读取URL文件失败: {str(e)}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Mobile Safari/537.36'
    }
    
    success_count = 0
    total_count = 0
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        
        if '#' in line:
            url, description = line.split('#', 1)
            url = url.strip()
            description = description.strip()
        else:
            url = line
            description = "无描述"
        
        if not url:
            continue
        
        total_count += 1
        
        try:
            response = requests.get(url, timeout=config_data['timeout'], headers=headers)
            
            if response.status_code == 200:
                logging.info(f"✓ 正常访问: {url} ({description}) - 状态码: {response.status_code}")
                success_count += 1
            else:
                logging.warning(f"网站访问异常: {url} ({description}) - 状态码: {response.status_code}")
                
                message = config_data['message_template'].format(
                    url=url,
                    description=description,
                    status_code=response.status_code,
                    timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                )
                
                send_wechat_message(config_data['webhook'], message)
        
        except requests.exceptions.Timeout:
            logging.warning(f"网站访问超时: {url} ({description})")
            
            message = config_data['message_template'].format(
                url=url,
                description=description,
                status_code="TIMEOUT",
                timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            )
            
            send_wechat_message(config_data['webhook'], message)
        
        except requests.exceptions.SSLError as e:
            # SSL证书错误不发送告警，只记录警告日志
            error_msg = str(e)
            logging.warning(f"网站SSL证书异常: {url} ({description}) - 错误: {error_msg}")
            # 注意：SSL证书错误不发送微信告警
        
        except requests.exceptions.RequestException as e:
            logging.warning(f"网站请求异常: {url} ({description}) - 错误: {str(e)}")
            
            message = config_data['message_template'].format(
                url=url,
                description=description,
                status_code=f"ERROR: {str(e)}",
                timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            )
            
            send_wechat_message(config_data['webhook'], message)
    
    return True, f"检查完成，共检查 {total_count} 个网站，成功 {success_count} 个"

def main():
    """主函数"""
    try:
        # 设置日志
        logger, log_path = setup_logging()
        
        logging.info("="*60)
        logging.info("网站监控脚本开始执行")
        logging.info(f"脚本目录: {get_script_directory()}")
        logging.info(f"当前工作目录: {os.getcwd()}")
        logging.info(f"Python路径: {sys.executable}")
        logging.info(f"日志文件路径: {log_path}")
        
        # 切换到脚本目录
        script_dir = get_script_directory()
        os.chdir(script_dir)
        logging.info(f"已切换到脚本目录: {os.getcwd()}")
        
        # 读取配置文件
        config_data, error_msg = read_config('config.conf')
        if config_data is None:
            logging.error(f"配置文件读取失败: {error_msg}")
            sys.exit(1)
        
        logging.info("配置文件读取成功")
        
        # 检查URLs
        success, msg = check_urls(config_data)
        if success:
            logging.info(msg)
        else:
            logging.error(msg)
        
        logging.info("网站监控脚本执行完成")
        logging.info("="*60)
        
    except Exception as e:
        error_msg = f"程序执行出错: {str(e)}"
        logging.error(error_msg)
        logging.error(traceback.format_exc())
        print(error_msg)
        sys.exit(1)

if __name__ == "__main__":
    main()