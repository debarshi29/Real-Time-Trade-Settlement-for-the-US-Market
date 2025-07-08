// contract_diagnostic.js - Diagnose deployment issues
async function main() {
    console.log("🔍 CONTRACT DEPLOYMENT DIAGNOSTIC");
    console.log("==================================");
    
    const [deployer] = await ethers.getSigners();
    console.log("🔑 Account:", deployer.address);
    
    // Check network
    const network = await ethers.provider.getNetwork();
    console.log("🌐 Network:", network.name, "Chain ID:", network.chainId.toString());
    
    const balance = await ethers.provider.getBalance(deployer.address);
    console.log("💰 Balance:", ethers.formatEther(balance), "ETH");
    
    // Addresses to check
    const TOKENIZED_CASH_ADDRESS = "0xD9C7441a4E845502bB22AbAbc370eF638405dbd3";
    const ATOMIC_SWAP_ADDRESS = "0x8e2D7F74874B150BE1ab18EdF9B8cb80eDD5A7DD";
    
    console.log("\n🔍 CHECKING CONTRACT ADDRESSES");
    console.log("==============================");
    
    // Check TokenizedCash
    console.log("\n📋 TokenizedCash Analysis:");
    console.log("Address:", TOKENIZED_CASH_ADDRESS);
    
    const tokenCode = await ethers.provider.getCode(TOKENIZED_CASH_ADDRESS);
    console.log("Code length:", tokenCode.length);
    console.log("Has code:", tokenCode !== "0x" ? "✅ YES" : "❌ NO");
    
    if (tokenCode === "0x") {
        console.log("🚨 TokenizedCash has NO CODE - deployment failed!");
    } else {
        console.log("✅ TokenizedCash has code deployed");
        console.log("Code preview:", tokenCode.substring(0, 100) + "...");
    }
    
    // Check AtomicSwap
    console.log("\n📋 AtomicSwap Analysis:");
    console.log("Address:", ATOMIC_SWAP_ADDRESS);
    
    const swapCode = await ethers.provider.getCode(ATOMIC_SWAP_ADDRESS);
    console.log("Code length:", swapCode.length);
    console.log("Has code:", swapCode !== "0x" ? "✅ YES" : "❌ NO");
    
    if (swapCode === "0x") {
        console.log("🚨 AtomicSwap has NO CODE - deployment failed!");
    } else {
        console.log("✅ AtomicSwap has code deployed");
        console.log("Code preview:", swapCode.substring(0, 100) + "...");
    }
    
    // Check recent transactions to find actual deployment
    console.log("\n🔍 RECENT TRANSACTION ANALYSIS");
    console.log("==============================");
    console.log("Analyzing recent transactions for contract deployments...");
    
    try {
        const currentBlock = await ethers.provider.getBlockNumber();
        console.log("Current block:", currentBlock);
        
        // Check last 10 blocks for transactions from deployer
        const searchBlocks = Math.min(10, currentBlock);
        let deploymentTxs = [];
        
        for (let i = 0; i < searchBlocks; i++) {
            const block = await ethers.provider.getBlock(currentBlock - i, true);
            if (block && block.transactions) {
                for (const tx of block.transactions) {
                    if (tx.from && tx.from.toLowerCase() === deployer.address.toLowerCase()) {
                        // Check if it's a contract deployment (to address is null)
                        if (tx.to === null) {
                            const receipt = await ethers.provider.getTransactionReceipt(tx.hash);
                            if (receipt && receipt.contractAddress) {
                                deploymentTxs.push({
                                    hash: tx.hash,
                                    contractAddress: receipt.contractAddress,
                                    gasUsed: receipt.gasUsed.toString(),
                                    status: receipt.status
                                });
                            }
                        }
                    }
                }
            }
        }
        
        if (deploymentTxs.length > 0) {
            console.log("\n🎯 FOUND CONTRACT DEPLOYMENTS:");
            deploymentTxs.forEach((deployment, index) => {
                console.log(`\n${index + 1}. Contract Deployment:`);
                console.log(`   📍 Address: ${deployment.contractAddress}`);
                console.log(`   🧾 Tx Hash: ${deployment.hash}`);
                console.log(`   ⛽ Gas Used: ${deployment.gasUsed}`);
                console.log(`   ✅ Status: ${deployment.status === 1 ? 'SUCCESS' : 'FAILED'}`);
            });
            
            console.log("\n💡 RECOMMENDATION:");
            console.log("Use one of the addresses above in your verification script!");
            
        } else {
            console.log("❌ No recent contract deployments found");
            console.log("💡 You may need to redeploy your contracts");
        }
        
    } catch (error) {
        console.log("❌ Error analyzing transactions:", error.message);
    }
    
    console.log("\n📋 DIAGNOSTIC SUMMARY");
    console.log("=====================");
    
    if (tokenCode === "0x" && swapCode === "0x") {
        console.log("🚨 BOTH contracts have no code - full redeployment needed");
    } else if (tokenCode === "0x") {
        console.log("🚨 TokenizedCash has no code - redeploy TokenizedCash");
    } else if (swapCode === "0x") {
        console.log("🚨 AtomicSwap has no code - redeploy AtomicSwap");
    } else {
        console.log("✅ Both contracts have code - check network/address mismatch");
    }
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error("Diagnostic failed:", error);
        process.exit(1);
    });