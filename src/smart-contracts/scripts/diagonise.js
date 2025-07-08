// scripts/diagnose_and_fix.js
const { ethers } = require("hardhat");

async function main() {
    console.log("🔍 CONTRACT DIAGNOSTIC AND RECOVERY");
    console.log("=====================================");
    
    const [deployer] = await ethers.getSigners();
    console.log("🔑 Account:", deployer.address);
    
    const balance = await ethers.provider.getBalance(deployer.address);
    console.log("💰 Balance:", ethers.formatEther(balance), "ETH");
    
    // Contract addresses from your deployment
    const TOKENIZED_CASH_ADDRESS = "0xD9C7441a4E845502bB22AbAbc370eF638405dbd3";
    
    console.log("\n🔍 DIAGNOSTIC PHASE");
    console.log("===================");
    
    // 1. Check if address has contract code
    console.log("\n1️⃣ Checking contract code...");
    const code = await ethers.provider.getCode(TOKENIZED_CASH_ADDRESS);
    console.log("Contract code length:", code.length);
    console.log("Has contract code:", code !== "0x");
    
    if (code === "0x") {
        console.log("❌ No contract code found at address!");
        console.log("📝 This means the contract was never deployed or deployment failed");
        
        // Check transaction history for this address
        console.log("\n2️⃣ Checking deployment transaction...");
        try {
            // Get recent blocks to find deployment
            const latestBlock = await ethers.provider.getBlockNumber();
            console.log("Latest block:", latestBlock);
            
            // Check last few blocks for contract creation
            for (let i = 0; i < 10; i++) {
                const blockNumber = latestBlock - i;
                const block = await ethers.provider.getBlock(blockNumber, true);
                
                for (const tx of block.transactions) {
                    if (tx.to === null && tx.from.toLowerCase() === deployer.address.toLowerCase()) {
                        console.log(`📦 Found contract creation tx in block ${blockNumber}:`, tx.hash);
                        
                        const receipt = await ethers.provider.getTransactionReceipt(tx.hash);
                        console.log("✅ Transaction status:", receipt.status === 1 ? "SUCCESS" : "FAILED");
                        console.log("📍 Contract address:", receipt.contractAddress);
                        
                        if (receipt.contractAddress && receipt.contractAddress !== TOKENIZED_CASH_ADDRESS) {
                            console.log("⚠️  Deployed address differs from expected!");
                            console.log("Expected:", TOKENIZED_CASH_ADDRESS);
                            console.log("Actual:", receipt.contractAddress);
                        }
                    }
                }
            }
        } catch (error) {
            console.log("Error checking deployment:", error.message);
        }
        
        console.log("\n🔧 RECOVERY: Redeploying contracts...");
        await redeployContracts();
        
    } else {
        console.log("✅ Contract code found, checking ABI compatibility...");
        
        // Try to create contract instance and test basic calls
        try {
            const TokenizedCash = await ethers.getContractFactory("TokenizedCash");
            const tokenizedCash = TokenizedCash.attach(TOKENIZED_CASH_ADDRESS);
            
            console.log("\n3️⃣ Testing contract calls...");
            
            // Test each function individually
            const tests = [
                { name: "name", func: () => tokenizedCash.name() },
                { name: "symbol", func: () => tokenizedCash.symbol() },
                { name: "decimals", func: () => tokenizedCash.decimals() },
                { name: "totalSupply", func: () => tokenizedCash.totalSupply() },
                { name: "balanceOf", func: () => tokenizedCash.balanceOf(deployer.address) }
            ];
            
            for (const test of tests) {
                try {
                    const result = await test.func();
                    console.log(`✅ ${test.name}():`, result.toString());
                } catch (error) {
                    console.log(`❌ ${test.name}():`, error.message);
                }
            }
            
        } catch (error) {
            console.log("❌ Failed to create contract instance:", error.message);
            console.log("🔧 Contract ABI mismatch - redeploying...");
            await redeployContracts();
        }
    }
}

async function redeployContracts() {
    console.log("\n🚀 REDEPLOYMENT PHASE");
    console.log("=====================");
    
    const [deployer] = await ethers.getSigners();
    
    try {
        // Deploy TokenizedCash
        console.log("\n📦 Deploying TokenizedCash...");
        const TokenizedCash = await ethers.getContractFactory("TokenizedCash");
        
        // Deploy with initial supply (1 million tokens)
        const initialSupply = ethers.parseEther("1000000"); // 1M tokens
        const tokenizedCash = await TokenizedCash.deploy(initialSupply);
        
        console.log("⏳ Waiting for deployment...");
        await tokenizedCash.waitForDeployment();
        
        const tokenizedCashAddress = await tokenizedCash.getAddress();
        console.log("✅ TokenizedCash deployed to:", tokenizedCashAddress);
        
        // Verify deployment
        console.log("\n🔍 Verifying deployment...");
        const name = await tokenizedCash.name();
        const symbol = await tokenizedCash.symbol();
        const decimals = await tokenizedCash.decimals();
        const totalSupply = await tokenizedCash.totalSupply();
        
        console.log("✅ Name:", name);
        console.log("✅ Symbol:", symbol);
        console.log("✅ Decimals:", decimals.toString());
        console.log("✅ Total Supply:", ethers.formatEther(totalSupply), "tokens");
        
        // Deploy TradeSettlement
        console.log("\n📦 Deploying TradeSettlement...");
        const TradeSettlement = await ethers.getContractFactory("TradeSettlement");
        
        const tradeSettlement = await TradeSettlement.deploy(
            tokenizedCashAddress
        );
        
        console.log("⏳ Waiting for TradeSettlement deployment...");
        await tradeSettlement.waitForDeployment();
        
        const tradeSettlementAddress = await tradeSettlement.getAddress();
        console.log("✅ TradeSettlement deployed to:", tradeSettlementAddress);
        
        // Update deployment record
        const deploymentInfo = {
            network: "besu",
            tokenizedCash: tokenizedCashAddress,
            tradeSettlement: tradeSettlementAddress,
            deployer: deployer.address,
            timestamp: new Date().toISOString(),
            blockNumber: await ethers.provider.getBlockNumber()
        };
        
        console.log("\n📝 DEPLOYMENT SUMMARY");
        console.log("=====================");
        console.log(JSON.stringify(deploymentInfo, null, 2));
        
        // Save to file
        const fs = require('fs');
        fs.writeFileSync('deployment-addresses.json', JSON.stringify(deploymentInfo, null, 2));
        console.log("💾 Deployment info saved to deployment-addresses.json");
        
        // Test the new deployment
        console.log("\n🧪 Testing new deployment...");
        await testContracts(tokenizedCash, tradeSettlement);
        
    } catch (error) {
        console.log("❌ Deployment failed:", error.message);
        
        if (error.message.includes("insufficient funds")) {
            console.log("💡 Solution: Add more ETH to your account");
        } else if (error.message.includes("gas")) {
            console.log("💡 Solution: Try adjusting gas settings");
        } else if (error.message.includes("revert")) {
            console.log("💡 Solution: Check constructor parameters");
        }
        
        throw error;
    }
}

async function testContracts(tokenizedCash, tradeSettlement) {
    const [deployer] = await ethers.getSigners();
    
    try {
        console.log("\n🧪 COMPREHENSIVE CONTRACT TESTING");
        console.log("==================================");
        
        // Test TokenizedCash
        console.log("\n💰 TokenizedCash Tests:");
        const balance = await tokenizedCash.balanceOf(deployer.address);
        console.log("✅ Deployer balance:", ethers.formatEther(balance), "tokens");
        
        // Test transfer
        const transferAmount = ethers.parseEther("100");
        const randomAddress = ethers.Wallet.createRandom().address;
        
        console.log("🔄 Testing transfer...");
        const transferTx = await tokenizedCash.transfer(randomAddress, transferAmount);
        await transferTx.wait();
        
        const newBalance = await tokenizedCash.balanceOf(randomAddress);
        console.log("✅ Transfer successful:", ethers.formatEther(newBalance), "tokens transferred");
        
        // Test TradeSettlement
        console.log("\n📋 TradeSettlement Tests:");
        const tokenAddress = await tradeSettlement.tokenizedCash();
        console.log("✅ Linked token address:", tokenAddress);
        
        // Test trade creation
        console.log("📝 Testing trade creation...");
        const tradeAmount = ethers.parseEther("50");
        const tradePrice = ethers.parseEther("100"); // 100 ETH per token
        
        const createTradeTx = await tradeSettlement.createTrade(
            randomAddress, // buyer
            tradeAmount,
            tradePrice
        );
        await createTradeTx.wait();
        
        const tradeCount = await tradeSettlement.tradeCounter();
        console.log("✅ Trade created, total trades:", tradeCount.toString());
        
        const trade = await tradeSettlement.trades(1);
        console.log("✅ Trade details:");
        console.log("   Seller:", trade.seller);
        console.log("   Buyer:", trade.buyer);
        console.log("   Amount:", ethers.formatEther(trade.amount));
        console.log("   Price:", ethers.formatEther(trade.price));
        console.log("   Status:", trade.status.toString());
        
        console.log("\n🎉 ALL TESTS PASSED!");
        console.log("=====================");
        
    } catch (error) {
        console.log("❌ Testing failed:", error.message);
        throw error;
    }
}

// Handle errors gracefully
main()
    .then(() => {
        console.log("\n✅ Diagnostic and recovery completed successfully!");
        process.exit(0);
    })
    .catch((error) => {
        console.error("\n❌ Diagnostic failed:", error.message);
        console.error("\n🔧 Troubleshooting steps:");
        console.error("1. Check your Besu node is running and accessible");
        console.error("2. Verify your account has sufficient ETH balance");
        console.error("3. Ensure your hardhat.config.js network settings are correct");
        console.error("4. Try restarting your Besu node");
        process.exit(1);
    });