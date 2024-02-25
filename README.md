# binance_auto_invest_bot

  - Regularly execute the spot trading pairs you want.  
  - Supports weekly, daily, hourly, and minutely trading frequencies.  
  - Multiple frequency trading can be excuted at the same time.  

## Install dependency packages

```
pip install binance-connector
```

## Create Binance API keys

  - Follow the steps in this link and you'll have API Key and Secret Key that will use later.
  - https://www.binance.com/en/support/faq/how-to-create-api-keys-on-binance-360002502072  

## Prepare config file

### Create an encrypted config file

  - The command zip -e will ask to set a password.
```
cd config
zip -e cfg.yaml.zip cfg.yaml
```

### Edit config file

  - Open cfg.yaml inside cfg.yaml.zip, don't use the original one which is not encrypted  
  - Copy and paste your API Key and Secret Key.  
  - Edit the order list follow the hints in config file.  

## Run

```
cd auto_invest_bot
chmod +x auto_invest_bot.py
python3 auto_invest_bot.py
```
   - Trading history will be stored in trading_history folder


