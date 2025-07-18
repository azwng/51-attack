import os
import sys
import numpy
import pylab
from heapq import *

from btcsim import *

#Kế thừa từ lớp Miner cơ bản
#Hành vi xấu: chỉ chấp nhận các block do chính nó đào được (t_block.miner_id != self.miner_id)
#Khi nhận block hợp lệ (do nó đào), nó sẽ cập nhật chain_head nếu block mới có height cao hơn
class BadMiner(Miner):
    def add_block(self, t_block):
        self.blocks[hash(t_block)] = t_block
        if (self.chain_head == '*'):
            self.chain_head = hash(t_block)
            self.mine_block()
            return
        # ignore all blocks that are not mined by myself
        if (t_block.miner_id != self.miner_id):
            self.blocks[hash(t_block)] = t_block
            return
        if (t_block.height > self.blocks[self.chain_head].height):
            self.chain_head = hash(t_block)
            self.announce_block(self.chain_head)
            self.mine_block()


#Khởi tạo thời gian, hàng đợi sự kiện và block gốc (genesis block)
t = 0.0
event_q = []

# root block
seed_block = Block(None, 0, t, -1, 0, 1)

#Tạo 6 miner với hash rate ngẫu nhiên
#Thiết lập một miner mạnh (attacker) chiếm 51% sức mạnh tính toán (để thực hiện tấn công 51%)

numminers = 6
hashrates = numpy.random.exponential(1.0, numminers)

# setup very strong miner
attacker_strength = 0.51
hashrates[numminers-1] = 0.0
hashrates[numminers-1] = hashrates.sum() * (attacker_strength/(1.0 - attacker_strength))

hashrates = hashrates/hashrates.sum()

miners = []
#Tạo mạng ngẫu nhiên giữa các miner với độ trễ và băng thông ngẫu nhiên
for i in range(numminers):
	miners.append(Miner(i, hashrates[i] * 1.0/600.0, 200*1024, seed_block, event_q, t))

# make the strong miner a bad miner
miners[i] = BadMiner(i, hashrates[i] * 1.0/600.0, 200*1024, seed_block, event_q, t)



# add some random links to each miner

for i in range(numminers):
	for k in range(4):
		j = numpy.random.randint(0, numminers)
		if i != j:
			latency = 0.020 + 0.200*numpy.random.random()
			bandwidth = 10*1024 + 200*1024*numpy.random.random()

			miners[i].add_link(j, latency, bandwidth)
			miners[j].add_link(i, latency, bandwidth)


# simulate some days of block generation
#Mô phỏng hoạt động trong 1 ngày (86400 giây)
#Xử lý các sự kiện theo thứ tự thời gian từ hàng đợi ưu tiên
curday = 0
maxdays = 5*7*24*60*60
maxdays = 1*24*60*60
while t < maxdays:
	t, t_event = heappop(event_q)
	#print('%08.3f: %02d->%02d %s' % (t, t_event.orig, t_event.dest, t_event.action), t_event.payload)
	miners[t_event.dest].receive_event(t, t_event)
	
	if t/(24*60*60) > curday:
		print('day %03d' % curday)
		curday = int(t/(24*60*60))+1



# data analysis

pylab.figure()

cols = ['r-', 'g-', 'b-', 'y-']

mine = miners[0]
t_hash = mine.chain_head

rewardsum = 0.0
for i in range(numminers):
	miners[i].reward = 0.0

main_chain = dict()
main_chain[hash(seed_block)] = 1

#Vẽ đồ thị thể hiện sự phát triển của chuỗi block chính theo thời gian
while t_hash != None:
	t_block = mine.blocks[t_hash]
	
	if t_hash not in main_chain:
		main_chain[t_hash] = 1
	
	miners[t_block.miner_id].reward += 1
	rewardsum += 1
	
	if t_block.prev != None:
		pylab.plot([mine.blocks[t_block.prev].time, t_block.time], [mine.blocks[t_block.prev].height, t_block.height], cols[t_block.miner_id%4])
	
	t_hash = t_block.prev

pylab.xlabel('time in s')
pylab.ylabel('block height')
pylab.draw()

pylab.figure()

pylab.plot([0, numpy.max(hashrates)*1.05], [0, numpy.max(hashrates)*1.05], '-', color='0.4')

#So sánh tỷ lệ hash rate và phần thưởng
#Vẽ đồ thị so sánh giữa hash rate của từng miner và phần thưởng tương ứng nhận được
for i in range(numminers):
	#print('%2d: %0.3f -> %0.3f' % (i, hashrates[i], miners[i].reward/rewardsum))
	pylab.plot(hashrates[i], miners[i].reward/rewardsum, 'k.')
pylab.plot(hashrates[i], miners[i].reward/rewardsum, 'rx')

pylab.xlabel('hashrate')
pylab.ylabel('reward')


#Đếm số block không nằm trong chuỗi chính (block mồ côi)
pylab.figure()
orphans = 0
for i in range(numminers):
	for t_hash in miners[i].blocks:
		if t_hash not in main_chain:
			orphans += 1
		# draws the chains
		if miners[i].blocks[t_hash].height > 1:
			cur_b = miners[i].blocks[t_hash]
			pre_b = miners[i].blocks[cur_b.prev]
			pylab.plot([hashrates[pre_b.miner_id], hashrates[cur_b.miner_id]], [pre_b.height, cur_b.height], 'k-')

pylab.ylabel('block height')
pylab.xlabel('hashrate')
pylab.ylim([0, 100])

print('Orphaned blocks: %d (%0.3f)' % (orphans, orphans/mine.blocks[mine.chain_head].height))
print('Average block height time: %0.3f min' % (mine.blocks[mine.chain_head].time/(60*mine.blocks[mine.chain_head].height)))




pylab.draw()
pylab.show()

