# binance_auto_invest_bot

Regularly execute the spot trading pairs you desired.  
Supports weekly, daily, hourly, and minutely trading frequencies.  
Supports multiple frequency trading at the same time.  

## Install dependency packages

```
pip install binance-connector
```

## Create Binance API keys

Follow the steps in this link and you'll have API Key and Secret Key that will use later.  
https://www.binance.com/en/support/faq/how-to-create-api-keys-on-binance-360002502072  

## Prepare config file

### Create an encrypted config file

```
cd config
zip --password <your password> cfg.yaml.zip cfg.yaml
```

### Edit config file

Open cfg.yaml inside cfg.yaml.zip  
Copy and paste your API Key and Secret Key.  
Edit the order list follow the hints.  


