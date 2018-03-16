#!/bin/bash
python3 run_communications_spiders.py &
sleep 1
python3 run_xuexin_spiders.py &
sleep 1
#python3 run_bank_spiders.py &
#sleep 1
python3 run_shixin_spiders.py &
sleep 1
python3 run_proxy_spiders.py &
sleep 1
python3 run_mobilebrand_spiders.py &