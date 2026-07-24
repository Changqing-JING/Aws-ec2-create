Install deps

```shell
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
aws sso login
```

Create instance

```shell
python create_ec2.py gpu --key-name YOUR_KEY_PAIR_NAME
```
