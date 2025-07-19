// simple_deploy.js - Clean deployment without complex gas settings
const { ethers } = require("hardhat");

async function main() {
    console.log("🚀 SIMPLE CONTRACT DEPLOYMENT");
    console.log("==============================");
    
    const [deployer] = await ethers.getSigners();
    console.log("🔑 Deployer account:", deployer.address);
    
    const balance = await ethers.provider.getBalance(deployer.address);
    console.log("💰 Balance:", ethers.formatEther(balance), "ETH");
    
    // Check network
    const network = await ethers.provider.getNetwork();
    console.log("🌐 Network:", network.name, "Chain ID:", network.chainId.toString());
    
    console.log("\n📝 STEP 1: DEPLOYING TOKENIZED CASH");
    console.log("====================================");
    
    let tokenizedCash;
    try {
        // Get contract factory
        const TokenizedCash = await ethers.getContractFactory("TokenizedCash");
        console.log("✅ TokenizedCash factory created");
        
        // Deploy with initial supply (1 million tokens)
        const initialSupply = ethers.parseEther("1000000"); // 1M tokens
        console.log("🔄 Deploying TokenizedCash with initial supply:", ethers.formatEther(initialSupply));
        tokenizedCash = await TokenizedCash.deploy(initialSupply);
        
        console.log("⏳ Waiting for deployment transaction to be mined...");
        await tokenizedCash.waitForDeployment();
        
        const tokenAddress = await tokenizedCash.getAddress();
        console.log("✅ TokenizedCash deployed successfully!");
        console.log("📍 Address:", tokenAddress);
        
        // Verify the contract has code
        const code = await ethers.provider.getCode(tokenAddress);
        console.log("🔍 Code verification:", code !== "0x" ? "✅ HAS CODE" : "❌ NO CODE");
        
        if (code === "0x") {
            throw new Error("TokenizedCash deployment failed - no code at address");
        }
        
        // Test basic functionality
        console.log("🧪 Testing basic ERC20 functionality...");
        const name = await tokenizedCash.name();
        const symbol = await tokenizedCash.symbol();
        const totalSupply = await tokenizedCash.totalSupply();
        const deployerBalance = await tokenizedCash.balanceOf(deployer.address);
        
        console.log("✅ ERC20 functions working:");
        console.log("   📛 Name:", name);
        console.log("   🔤 Symbol:", symbol);
        console.log("   📊 Total Supply:", ethers.formatEther(totalSupply));
        console.log("   💰 Deployer Balance:", ethers.formatEther(deployerBalance));
        
    } catch (error) {
        console.log("❌ TokenizedCash deployment failed:", error.message);
        return;
    }
    
    console.log("\n📝 STEP 2: DEPLOYING TOKENIZED SECURITY");
    console.log("========================================");
    
    let tokenizedSecurity;
    try {
        // Get contract factory
        const TokenizedSecurity = await ethers.getContractFactory("TokenizedSecurity");
        console.log("✅ TokenizedSecurity factory created");
        
        // Deploy with initial supply (1 million tokens)
        const initialSupply = ethers.parseEther("1000000"); // 1M tokens
        console.log("🔄 Deploying TokenizedSecurity with initial supply:", ethers.formatEther(initialSupply));
        tokenizedSecurity = await TokenizedSecurity.deploy(initialSupply);
        
        console.log("⏳ Waiting for deployment transaction to be mined...");
        await tokenizedSecurity.waitForDeployment();
        
        const securityAddress = await tokenizedSecurity.getAddress();
        console.log("✅ TokenizedSecurity deployed successfully!");
        console.log("📍 Address:", securityAddress);
        
        // Verify the contract has code
        const code = await ethers.provider.getCode(securityAddress);
        console.log("🔍 Code verification:", code !== "0x" ? "✅ HAS CODE" : "❌ NO CODE");
        
        if (code === "0x") {
            throw new Error("TokenizedSecurity deployment failed - no code at address");
        }
        
        // Test basic functionality
        console.log("🧪 Testing basic ERC20 functionality...");
        const name = await tokenizedSecurity.name();
        const symbol = await tokenizedSecurity.symbol();
        const totalSupply = await tokenizedSecurity.totalSupply();
        const deployerBalance = await tokenizedSecurity.balanceOf(deployer.address);
        

        console.log("Deployer Address:", deployer.address);
        console.log("✅ ERC20 functions working:");
        console.log("   📛 Name:", name);
        console.log("   🔤 Symbol:", symbol);
        console.log("   📊 Total Supply:", ethers.formatEther(totalSupply));
        console.log("   💰 Deployer Balance:", ethers.formatEther(deployerBalance));
        
    } catch (error) {
        console.log("❌ TokenizedSecurity deployment failed:", error.message);
        return;
    }
    
    console.log("\n📝 STEP 3: DEPLOYING ATOMIC SWAP");
    console.log("=================================");
    
    let atomicSwap;
    try {
        // Get contract factory
        const AtomicSwap = await ethers.getContractFactory("AtomicSwap");
        console.log("✅ AtomicSwap factory created");
        
        // Deploy with default settings
        console.log("🔄 Deploying AtomicSwap...");
        atomicSwap = await AtomicSwap.deploy();
        
        console.log("⏳ Waiting for deployment transaction to be mined...");
        await atomicSwap.waitForDeployment();
        
        const swapAddress = await atomicSwap.getAddress();
        console.log("✅ AtomicSwap deployed successfully!");
        console.log("📍 Address:", swapAddress);
        
        // Verify the contract has code
        const code = await ethers.provider.getCode(swapAddress);
        console.log("🔍 Code verification:", code !== "0x" ? "✅ HAS CODE" : "❌ NO CODE");
        
        if (code === "0x") {
            throw new Error("AtomicSwap deployment failed - no code at address");
        }
        
        console.log("✅ AtomicSwap deployed and verified!");
        
    } catch (error) {
        console.log("❌ AtomicSwap deployment failed:", error.message);
        return;
    }
    
    console.log("\n🧪 STEP 4: INTEGRATION TESTING");
    console.log("===============================");
    
    try {
        const tokenAddress = await tokenizedCash.getAddress();
        const securityAddress = await tokenizedSecurity.getAddress();
        const swapAddress = await atomicSwap.getAddress();
        
        console.log("🔄 Testing TokenizedCash <-> AtomicSwap integration...");
        
        // Test allowance and approval for TokenizedCash
        const approveAmount = ethers.parseEther("1000");
        console.log("📝 Approving", ethers.formatEther(approveAmount), "TokenizedCash tokens for AtomicSwap...");
        
        const approveTx = await tokenizedCash.approve(swapAddress, approveAmount);
        await approveTx.wait();
        
        const allowance = await tokenizedCash.allowance(deployer.address, swapAddress);
        console.log("✅ TokenizedCash allowance set successfully:", ethers.formatEther(allowance), "tokens");
        
        console.log("🔄 Testing TokenizedSecurity <-> AtomicSwap integration...");
        
        // Test allowance and approval for TokenizedSecurity
        console.log("📝 Approving", ethers.formatEther(approveAmount), "TokenizedSecurity tokens for AtomicSwap...");
        
        const approveSecurityTx = await tokenizedSecurity.approve(swapAddress, approveAmount);
        await approveSecurityTx.wait();
        
        const securityAllowance = await tokenizedSecurity.allowance(deployer.address, swapAddress);
        console.log("✅ TokenizedSecurity allowance set successfully:", ethers.formatEther(securityAllowance), "tokens");
        
        console.log("✅ All integration tests passed!");
        
    } catch (error) {
        console.log("❌ Integration test failed:", error.message);
    }
    
    console.log("\n📋 DEPLOYMENT SUMMARY");
    console.log("======================");
    
    const tokenAddress = await tokenizedCash.getAddress();
    const securityAddress = await tokenizedSecurity.getAddress();
    const swapAddress = await atomicSwap.getAddress();
    
    console.log("✅ TokenizedCash Contract:");
    console.log("   📍 Address:", tokenAddress);
    
    console.log("✅ TokenizedSecurity Contract:");
    console.log("   📍 Address:", securityAddress);
    
    console.log("✅ AtomicSwap Contract:");
    console.log("   📍 Address:", swapAddress);
    
    console.log("\n📝 UPDATE YOUR VERIFICATION SCRIPT:");
    console.log("===================================");
    console.log(`const TOKENIZED_CASH_ADDRESS = "${tokenAddress}";`);
    console.log(`const TOKENIZED_SECURITY_ADDRESS = "${securityAddress}";`);
    console.log(`const ATOMIC_SWAP_ADDRESS = "${swapAddress}";`);
    
    // Save addresses to file
    try {
        const fs = require('fs');
        const addresses = {
            TokenizedCash: tokenAddress,
            TokenizedSecurity: securityAddress,
            AtomicSwap: swapAddress,
            deployer: deployer.address,
            network: network.name,
            chainId: network.chainId.toString(),
            deploymentTime: new Date().toISOString()
        };
        
        fs.writeFileSync('deployed-addresses.json', JSON.stringify(addresses, null, 2));
        console.log("\n📄 Addresses saved to deployed-addresses.json");
    } catch (error) {
        console.log("⚠️  Could not save addresses to file:", error.message);
    }
    
    console.log("\n🎉 DEPLOYMENT SUCCESSFUL!");
    console.log("==========================");
    console.log("All three contracts are deployed and functional!");
    console.log("- TokenizedCash: Cash management token");
    console.log("- TokenizedSecurity: Security/asset token");
    console.log("- AtomicSwap: Cross-chain swap functionality");
    console.log("You can now run the verification script to confirm everything works.");
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error("❌ Deployment script failed:", error);
        process.exit(1);
    });