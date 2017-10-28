#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import hashlib
import hmac
import time
import json
import urllib.parse
from itertools import count
from datetime import datetime
from bs4 import BeautifulSoup
import config as cfg


def dict_add(a, b):
    for k2, v2 in b.items():    
        if k2 in a.keys():
            a[k2] += v2
        else:
            a[k2] = v2
    return a


def get_ether(address):
    url = 'https://etherscan.io/address/' + address
    r = requests.get(url)
    soup = BeautifulSoup(r.text, 'html.parser')
    eth = soup.find_all('table')[0].find_all('td')[1].text.replace('\n','').split(' ')[0]
    eth = float(eth.replace(',', ''))
    assets = {'ETH': eth}
    balancelist = soup.find(id='balancelist')
    for i in balancelist.find_all('li')[:-1]:
        br = i.a.br.text.split('@')[0]
        token = br.split(' ')[1]
        amount = float(br.split(' ')[0].replace(',', ''))
        if token in assets.keys():
            print('Warning: Duplicated token symbol {0}. Using the first one.'.format(token))
            continue
        assets[token] = amount
    return assets


def get_bittrex(apikey, apisecret):
    nonce = str(datetime.timestamp(datetime.now()))
    url = 'https://bittrex.com/api/v1.1/account/getbalances?apikey={0}&nonce={1}'.format(apikey,nonce)
    sign = hmac.new(apisecret, url.encode('utf-8'), hashlib.sha512).hexdigest()
    
    
    headers = {'apisign': sign}
    r = requests.get(url, headers=headers)
    balance = r.json()['result']
    assets = {}
    for i in balance:
        token = i['Currency']
        amount = i['Balance']
        if amount == 0: continue
        assets[token] = amount
    return assets


def get_poloniex(apikey, apisecret):
    nonce_counter = count(int(time.time() * 1000))    
    url = 'https://poloniex.com/tradingApi'
    payload = {'command': 'returnCompleteBalances',
                'account': 'all',
                'nonce': next(nonce_counter)}
    paybytes = urllib.parse.urlencode(payload).encode('utf8')
    sign = hmac.new(apisecret, paybytes, hashlib.sha512)
    headers = {'Key': apikey,
               'Sign': sign.hexdigest()}
    
    r = requests.post(url, data=payload, headers=headers)
    balance = r.json()
    
    assets = {}
    for k in balance.keys():
        onOrders = float(balance[k]['onOrders'])
        available = float(balance[k]['available'])
        if onOrders + available == 0: continue
        assets[k] = onOrders + available
    return assets


def get_bitfinex(apikey, apisecret):
    baseurl = 'https://api.bitfinex.com/'
    path = 'v2/auth/r/wallets'
    nonce = str(datetime.timestamp(datetime.now()))
    body = {}
    rawBody = json.dumps(body)
    signature = "/api/" + path + nonce + rawBody
    signature = hmac.new(apisecret, signature.encode('utf-8'), hashlib.sha384).hexdigest()
    headers = {
                "bfx-nonce": nonce,
                "bfx-apikey": apikey,
                "bfx-signature": signature,
                "content-type": "application/json"
            }
    r = requests.post(baseurl+path, headers=headers, data=rawBody, verify=True)
    
    balance = r.json()
    assets = {}
    for i in balance:
        token = i[1]
        amount = i[2]
        if amount == 0: continue
        assets[token] = amount
    return assets


def get_price(coins):
    capital = {}
    
    url = 'https://api.coinmarketcap.com/v1/ticker/?convert=CNY'
    r = requests.get(url)
    prices = r.json()
    
    for i in prices:
        token = i['symbol']
        #TODO: workaround for different use of symbols across platforms, but there must be a neat way!
        if i['id'] == 'iota': token = 'IOT'
        if i['id'] == 'kingn-coin': token = 'KNGC'
        if i['id'] == 'cryptonex': token = 'CNXCOIN'
        if token in coins.keys():
            capital[token] = float(i['price_cny']) * coins[token]

    return capital


def fetch_data():
    mycoins = cfg.other_bl
    
    #Etherscan
    if cfg.addresses != []:
        for address in cfg.addresses:
            assets = get_ether(address)
            mycoins = dict_add(mycoins, assets)
        
    #Bittrex 
    if cfg.bittrex_apikey != '':
        assets = get_bittrex(cfg.bittrex_apikey, cfg.bittrex_apisecret)
        mycoins = dict_add(mycoins, assets)
    
    #Poloniex
    if cfg.poloniex_apikey != '':
        assets = get_poloniex(cfg.poloniex_apikey, cfg.poloniex_apisecret)
        mycoins = dict_add(mycoins, assets)
    
    #Bitfinex
    if cfg.bitfinex_apikey != '':
        assets = get_bitfinex(cfg.bitfinex_apikey, cfg.bitfinex_apisecret)
        mycoins = dict_add(mycoins, assets)
        
    print(mycoins)
    
    #coinmarketcap
    capital = get_price(mycoins)
    print(capital)
    return (capital, mycoins)
    
    
if __name__ == '__main__':
    fetch_data()
