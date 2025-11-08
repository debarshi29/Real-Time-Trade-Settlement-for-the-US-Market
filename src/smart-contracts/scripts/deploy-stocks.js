// deploy-stocks.js - Deploy multiple stock tokens
const { ethers } = require("hardhat");
const fs = require('fs');

async function main() {
    console.log("🚀 MULTIPLE STOCK TOKENS DEPLOYMENT");
    console.log("====================================");
    
    const [deployer] = await ethers.getSigners();
    console.log("🔑 Deployer account:", deployer.address);
    
    const balance = await ethers.provider.getBalance(deployer.address);
    console.log("💰 Balance:", ethers.formatEther(balance), "ETH");
    
    // Check network
    const network = await ethers.provider.getNetwork();
    console.log("🌐 Network:", network.name, "Chain ID:", network.chainId.toString());
    
    // Define the 5 stocks to deploy
    const stocks = [
        { name: "Apple Stock", symbol: "AAPL", initialSupply: "1000000" },
        { name: "Google Stock", symbol: "GOOGL", initialSupply: "500000" },
        { name: "Tesla Stock", symbol: "TSLA", initialSupply: "750000" },
        { name: "Amazon Stock", symbol: "AMZN", initialSupply: "600000" },
        { name: "Microsoft Stock", symbol: "MSFT", initialSupply: "800000" }
    ];
    
    const deployedStocks = {};
    
    // Deploy each stock token
    for (let i = 0; i < stocks.length; i++) {
        const stock = stocks[i];
        
        console.log(`\n📝 STEP ${i + 1}: DEPLOYING ${stock.name.toUpperCase()}`);
        console.log("=".repeat(50));
        
        try {
            // Get contract factory
            const TokenizedSecurity = await ethers.getContractFactory("TokenizedSecurity");
            console.log(`✅ ${stock.symbol} factory created`);
            
            // Deploy with name, symbol, and initial supply
            const initialSupply = ethers.parseEther(stock.initialSupply);
            console.log(`🔄 Deploying ${stock.name} (${stock.symbol})`);
            console.log(`   Initial Supply: ${ethers.formatEther(initialSupply)} tokens`);
            
            const tokenContract = await TokenizedSecurity.deploy(
                stock.name,
                stock.symbol,
                stock.initialSupply
            );
            
            console.log("⏳ Waiting for deployment transaction to be mined...");
            await tokenContract.waitForDeployment();
            
            const tokenAddress = await tokenContract.getAddress();
            console.log(`✅ ${stock.symbol} deployed successfully!`);
            console.log(`📍 Address: ${tokenAddress}`);
            
            // Verify the contract has code
            const code = await ethers.provider.getCode(tokenAddress);
            console.log("🔍 Code verification:", code !== "0x" ? "✅ HAS CODE" : "❌ NO CODE");
            
            if (code === "0x") {
                throw new Error(`${stock.symbol} deployment failed - no code at address`);
            }
            
            // Test basic functionality
            console.log("🧪 Testing basic ERC20 functionality...");
            const name = await tokenContract.name();
            const symbol = await tokenContract.symbol();
            const totalSupply = await tokenContract.totalSupply();
            const deployerBalance = await tokenContract.balanceOf(deployer.address);
            
            console.log("✅ ERC20 functions working:");
            console.log("   📛 Name:", name);
            console.log("   🔤 Symbol:", symbol);
            console.log("   📊 Total Supply:", ethers.formatEther(totalSupply));
            console.log("   💰 Deployer Balance:", ethers.formatEther(deployerBalance));
            
            // Store deployed address
            deployedStocks[stock.symbol] = {
                address: tokenAddress,
                name: stock.name,
                symbol: stock.symbol,
                totalSupply: ethers.formatEther(totalSupply)
            };
            
        } catch (error) {
            console.log(`❌ ${stock.symbol} deployment failed:`, error.message);
            return;
        }
    }
    
    console.log("\n📋 DEPLOYMENT SUMMARY");
    console.log("=".repeat(50));
    
    for (const [symbol, info] of Object.entries(deployedStocks)) {
        console.log(`✅ ${info.name} (${symbol}):`);
        console.log(`   📍 Address: ${info.address}`);
        console.log(`   📊 Total Supply: ${info.totalSupply}`);
    }
    
    console.log("\n📝 UPDATE YOUR SCRIPTS:");
    console.log("=".repeat(50));
    for (const [symbol, info] of Object.entries(deployedStocks)) {
        console.log(`const ${symbol}_ADDRESS = "${info.address}";`);
    }
    
    // Load existing addresses if available
    let existingAddresses = {};
    if (fs.existsSync('deployed-addresses-1.json')) {
        try {
            const fileContent = fs.readFileSync('deployed-addresses-1.json', 'utf8');
            existingAddresses = JSON.parse(fileContent);
            console.log("\n📄 Loaded existing deployed-addresses.json");
        } catch (error) {
            console.log("⚠️  Could not load existing addresses:", error.message);
        }
    }
    
    // Merge stock addresses with existing addresses
    const stockAddresses = {};
    for (const [symbol, info] of Object.entries(deployedStocks)) {
        stockAddresses[symbol] = info.address;
    }
    
    const updatedAddresses = {
        ...existingAddresses,
        ...stockAddresses,
        deployer: deployer.address,
        network: network.name,
        chainId: network.chainId.toString(),
        lastStockDeployment: new Date().toISOString()
    };
    
    // Save addresses to file
    try {
        fs.writeFileSync('deployed-addresses-1.json', JSON.stringify(updatedAddresses, null, 2));
        console.log("\n📄 Addresses saved to deployed-addresses-1.json");
        console.log("\n📦 Updated deployed-addresses-1.json contents:");
        console.log(JSON.stringify(updatedAddresses, null, 2));
    } catch (error) {
        console.log("⚠️  Could not save addresses to file:", error.message);
    }
    
    console.log("\n🎉 STOCK DEPLOYMENT SUCCESSFUL!");
    console.log("=".repeat(50));
    console.log("All 5 stock tokens are deployed and functional!");
    console.log("- AAPL: Apple Stock");
    console.log("- GOOGL: Google Stock");
    console.log("- TSLA: Tesla Stock");
    console.log("- AMZN: Amazon Stock");
    console.log("- MSFT: Microsoft Stock");
    console.log("\nYou can now run fund_accounts.py to distribute tokens.");
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error("❌ Deployment script failed:", error);
        process.exit(1);
    });