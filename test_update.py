from AccessingWFMarket import updateListing
# Pick a random ID from your logs that you know exists
test_id = "6a3feb2b86fc399ad4a9876f" 
success = updateListing(test_id, 70, 1, True, "Test_Item", "buy")
print(f"Update Success: {success}")
