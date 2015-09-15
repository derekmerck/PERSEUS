
FileName = 'RIHEDUrg CDev-03MP90_ECG_I_20150907_125701.txt'
%FileName = 'RIHEDUrg CDev-03MP90_PLETH_20150907_125701.txt'


Fid = fopen(FileName);

Temp = fread(Fid,[3 inf],'uint16');

fclose(Fid);

% the first 4 bytes (32 bits) of each sample is time in milli seconds

Time = Temp(1,:) + Temp(2,:)*2^16 ;

Time = Time / 1000; % Convert the time to second

% two bytes are data
Data = Temp(3,:);

plot(Time,Data)

xlabel('Time (Second)','fontsize',14)
ylabel('value','fontsize',14)
title('Time of the samples','fontsize',14)