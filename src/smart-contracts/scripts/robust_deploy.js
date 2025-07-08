// robust_deploy.js - Deploy with proper error handling and verification
async function main() {
    console.log("🚀 ROBUST CONTRACT DEPLOYMENT");
    console.log("==============================");
    
    const [deployer] = await ethers.getSigners();
    console.log("🔑 Deployer account:", deployer.address);
    
    const balance = await ethers.provider.getBalance(deployer.address);
    console.log("💰 Balance:", ethers.formatEther(balance), "ETH");
    
    // Check network
    const network = await ethers.provider.getNetwork();
    console.log("🌐 Network:", network.name, "Chain ID:", network.chainId.toString());
    
    if (balance < ethers.parseEther("0.1")) {
        console.log("❌ Insufficient balance for deployment");
        return;
    }
    
    console.log("\n📝 STEP 1: DEPLOYING TOKENIZED CASH");
    console.log("====================================");
    
    let tokenizedCash;
    try {
        // Get contract factory
        const TokenizedCash = await ethers.getContractFactory("TokenizedCash");
        console.log("✅ Contract factory created");
        
        // Deploy with explicit gas settings
        console.log("🔄 Deploying TokenizedCash...");
        tokenizedCash = await TokenizedCash.deploy({
            gasLimit: 3000000, // Explicit gas limit
            gasPrice: ethers.parseUnits("20", "gwei") // Explicit gas price
        });
        
        console.log("⏳ Waiting for deployment transaction...");
        console.log("📊 Transaction Hash:", tokenizedCash.deploymentTransaction().hash);
        
        // Wait for deployment to be mined
        await tokenizedCash.deploymentTransaction().wait();
        
        console.log("✅ TokenizedCash deployed successfully!");
        console.log("📍 Address:", await tokenizedCash.getAddress());
        
        // Verify the contract has code
        const tokenAddress = await tokenizedCash.getAddress();
        const code = await ethers.provider.getCode(tokenAddress);
        console.log("🔍 Code verification:", code !== "0x" ? "✅ HAS CODE" : "❌ NO CODE");
        
        if (code === "0x") {
            throw new Error("TokenizedCash deployment failed - no code at address");
        }
        
        // Test basic functionality
        console.log("🧪 Testing basic functionality...");
        const name = await tokenizedCash.name();
        const symbol = await tokenizedCash.symbol();
        const totalSupply = await tokenizedCash.totalSupply();
        
        console.log("✅ Basic functions working:");
        console.log("   📛 Name:", name);
        console.log("   🔤 Symbol:", symbol);
        console.log("   📊 Total Supply:", ethers.formatEther(totalSupply));
        
    } catch (error) {
        console.log("❌ TokenizedCash deployment failed:", error.message);
        console.log("🔍 Error details:", error);
        return;
    }
    
    console.log("\n📝 STEP 2: DEPLOYING ATOMIC SWAP");
    console.log("=================================");
    
    let atomicSwap;
    try {
        // Get contract factory
        const AtomicSwap = await ethers.getContractFactory("AtomicSwap");
        console.log("✅ Contract factory created");
        
        // Deploy with explicit gas settings
        console.log("🔄 Deploying AtomicSwap...");
        atomicSwap = await AtomicSwap.deploy({
            gasLimit: 3000000, // Explicit gas limit
            gasPrice: ethers.parseUnits("20", "gwei") // Explicit gas price
        });
        
        console.log("⏳ Waiting for deployment transaction...");
        console.log("📊 Transaction Hash:", atomicSwap.deploymentTransaction().hash);
        
        // Wait for deployment to be mined
        await atomicSwap.deploymentTransaction().wait();
        
        console.log("✅ AtomicSwap deployed successfully!");
        console.log("📍 Address:", await atomicSwap.getAddress());
        
        // Verify the contract has code
        const swapAddress = await atomicSwap.getAddress();
        const code = await ethers.provider.getCode(swapAddress);
        console.log("🔍 Code verification:", code !== "0x" ? "✅ HAS CODE" : "❌ NO CODE");
        
        if (code === "0x") {
            throw new Error("AtomicSwap deployment failed - no code at address");
        }
        
        console.log("✅ AtomicSwap deployed and verified!");
        
    } catch (error) {
        console.log("❌ AtomicSwap deployment failed:", error.message);
        console.log("🔍 Error details:", error);
        return;
    }
    
    console.log("\n🧪 STEP 3: INTEGRATION TESTING");
    console.log("===============================");
    
    try {
        const tokenAddress = await tokenizedCash.getAddress();
        const swapAddress = await atomicSwap.getAddress();
        
        console.log("🔄 Testing ERC20 -> AtomicSwap integration...");
        
        // Test allowance and approval
        const approveAmount = ethers.parseEther("1000");
        console.log("📝 Approving", ethers.formatEther(approveAmount), "tokens for AtomicSwap...");
        
        const approveTx = await tokenizedCash.approve(swapAddress, approveAmount);
        await approveTx.wait();
        
        const allowance = await tokenizedCash.allowance(deployer.address, swapAddress);
        console.log("✅ Allowance set:", ethers.formatEther(allowance), "tokens");
        
        console.log("✅ Integration test successful!");
        
    } catch (error) {
        console.log("❌ Integration test failed:", error.message);
    }
    
    console.log("\n📋 DEPLOYMENT SUMMARY");
    console.log("======================");
    
    const tokenAddress = await tokenizedCash.getAddress();
    const swapAddress = await atomicSwap.getAddress();
    
    console.log("✅ TokenizedCash:");
    console.log("   📍 Address:", tokenAddress);
    console.log("   🧾 Tx Hash:", tokenizedCash.deploymentTransaction().hash);
    
    console.log("✅ AtomicSwap:");
    console.log("   📍 Address:", swapAddress);
    console.log("   🧾 Tx Hash:", atomicSwap.deploymentTransaction().hash);
    
    console.log("\n📝 NEXT STEPS:");
    console.log("==============");
    console.log("1. Update your verification script with these addresses:");
    console.log(`   const TOKENIZED_CASH_ADDRESS = "${tokenAddress}";`);
    console.log(`   const ATOMIC_SWAP_ADDRESS = "${swapAddress}";`);
    console.log("\n2. Run your verification script to confirm everything works");
    
    // Write addresses to a file for easy access
    const fs = require('fs');
    const addresses = {
        TokenizedCash: tokenAddress,
        AtomicSwap: swapAddress,
        deployer: deployer.address,
        network: network.name,
        chainId: network.chainId.toString()
    };
    
    fs.writeFileSync('deployed-addresses.json', JSON.stringify(addresses, null, 2));
    console.log("\n📄 Addresses saved to deployed-addresses.json");
    
    console.log("\n🎉 DEPLOYMENT COMPLETE!");
    console.log("========================");
    console.log("Both contracts deployed successfully and verified!");
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error("❌ Deployment failed:", error);
        process.exit(1);
    });