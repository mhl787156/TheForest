import csv
import matplotlib.pyplot as plt  
import numpy as np

timestamps = []
touch_statuses = []

with open('raveforest_data_2023-10-08-17-56-28.csv') as f:
  reader = csv.reader(f)
  for i, row in enumerate(reader):
    timestamps.append(row[0])   
    data = eval(row[2])
    for rave in data.values():
      touch_statuses.append(rave['touch_status'])
      
# Downsample sensor data to match timestamps length  
fig, ax = plt.subplots()
colors = ['blue', 'red', 'green', 'orange', 'purple', 'brown']
for i in range(6):

  sensor_data = np.array([ts[i] for ts in touch_statuses])[::6]
  
  ax.plot(timestamps, sensor_data, 'x', color=colors[i])

ax.set_ylim(-0.5, 5.5)
ax.set_yticks(range(6))
ax.set_yticklabels(['S1', 'S2', 'S3', 'S4', 'S5', 'S6']) 
ax.set_xlabel('Timestamp')
ax.set_title('Touch Status Over Time')

plt.show()