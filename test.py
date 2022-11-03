nums = [1,15,32,44,64,434,34534,1024]

for i in nums:
    if i % 32 == 0:
        print(f"YES {i}")
    else:
        print(f"NO {i}")