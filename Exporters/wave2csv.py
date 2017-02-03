

""""
1. Read json export
2. For each item
3.   Create 64 increments over 1/4 of a second
4.   Zip ecg
5.   Zip pleth with every other
6.   Add qos to beginning
7.   Output those 64 timestamps as csv


timestamp     ,    ecg     ,    pleth     ,   qos
-------------------------------------------------------
ts + incr 0   ,    ecg0    ,    pleth0    ,   qos0
ts + incr 1   ,    ecg1    ,    -----     ,   -----
ts + incr 2   ,    ecg2    ,    pleth1    ,   -----
ts + incr 3   ,    ecg3    ,    -----     ,   -----


""""