# web-check
一个访问指定url，不通则发送企微告警的程序，该脚本没有定时功能，定时功能需要自行在服务器上配置

url文件是：url.txt 书写规范是：https://www.baidu.com#百度网站

配置文件在：config.conf

配置参数有：

[webhook]

webhook=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxxxxxxxxxxxxxxxxxxxxxxxxxxx

[url]

url=url.txt

[timeout]

timeout=10

[moban]

moban=【网站监控告警】

时间: {timestamp}

网站: {url}

描述: {description}

状态: {status_code}

结果: 无法访问


[logfile]

logfile=./logs


windows上启动一分钟执行一次的计划任务：

schtasks /create /tn "网站监控脚本" /tr "\"C:Python\Python314\python.exe\" \"C:webcheck.py\"" /sc minute /mo 1 /ru "SYSTEM" /f
