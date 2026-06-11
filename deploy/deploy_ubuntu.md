# Ubuntu 部署说明

推荐环境：Ubuntu 22.04、Python 3.10+、Streamlit、开放 TCP 8501 端口。

```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv git -y

git clone <your_repo_url>
cd digital_employee_daily_report

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
streamlit run app.py --server.port 8501 --server.address 0.0.0.0
```

浏览器访问：

```text
http://服务器公网IP:8501
```

如果使用云服务器，需要在安全组中放行 TCP 8501。
