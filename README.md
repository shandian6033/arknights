# arknights
## 本程序多为自娱自乐
基本思路：

根据需求，利用linear program求解。方程大致为

min 理智消耗(各关理智(Ct) * 通关次数(X))

such that 获取材料(各关爆率(A) * 通关次数(X)) >= 需求(b)

## 食用说明
### 1. 在all_in_one.xlsx的Demand页的Demand列中输入需要的材料：
负数为已拥有的数量，正数为需要的数量
### 2. 运行arknights.py
需要Python3及package: pandas, scipy
### 3. 运行成功显示Success，否则为Fail
### 4. 结果在all_in_one.xlsx的Todo页
基于需求的材料价值在Demand页的Value列：单位为理智
#### 注： 价值不考虑赤金带来的收益

数据来源于https://penguin-stats.io/
感谢[AlvlSsReimu](https://github.com/AlvISsReimu)的支持

## 意见及BUG
有任何问题欢迎创建Issue
