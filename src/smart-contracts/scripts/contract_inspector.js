// Contract Inspector Script
// This will help diagnose what functions are available on your deployed contracts

const { ethers } = require("hardhat");

async function main() {
    console.log("🔍 Inspecting deployed contracts...\n");

    const TOKENIZED_CASH_ADDRESS = "0xF5f0b6c754226E67B723226C72d9451f9E2b68B5";
    const ATOMIC_SWAP_ADDRESS = "0xdF65C3d00b1021Fd667831D79915cB0321915AbC";
    
    const [deployer] = await ethers.getSigners();
    console.log("🔑 Using account:", deployer.address);

    try {
        // Inspect TokenizedCash contract
        console.log("🪙 TOKENIZED CASH CONTRACT INSPECTION");
        console.log("=====================================");
        console.log("Address:", TOKENIZED_CASH_ADDRESS);
        
        // Try to get the contract factory and ABI
        try {
            const TokenizedCash = await ethers.getContractFactory("TokenizedCash");
            const tokenizedCash = TokenizedCash.attach(TOKENIZED_CASH_ADDRESS);
            
            console.log("\n📋 Available functions from ABI:");
            const abi = TokenizedCash.interface;
            
            // List all functions
            Object.keys(abi.functions).forEach(func => {
                console.log(`   - ${func}`);
            });
            
            // Test basic ERC20 functions
            console.log("\n🧪 Testing basic ERC20 functions:");
            
            try {
                const name = await tokenizedCash.name();
                console.log("   ✅ name():", name);
            } catch (e) {
                console.log("   ❌ name() failed:", e.message);
            }
            
            try {
                const symbol = await tokenizedCash.symbol();
                console.log("   ✅ symbol():", symbol);
            } catch (e) {
                console.log("   ❌ symbol() failed:", e.message);
            }
            
            try {
                const decimals = await tokenizedCash.decimals();
                console.log("   ✅ decimals():", decimals.toString());
            } catch (e) {
                console.log("   ❌ decimals() failed:", e.message);
            }
            
            try {
                const totalSupply = await tokenizedCash.totalSupply();
                console.log("   ✅ totalSupply():", ethers.formatUnits(totalSupply, 18));
            } catch (e) {
                console.log("   ❌ totalSupply() failed:", e.message);
            }
            
            // Test owner function (might not exist)
            try {
                const owner = await tokenizedCash.owner();
                console.log("   ✅ owner():", owner);
            } catch (e) {
                console.log("   ❌ owner() failed:", e.message);
                
                // Try alternative owner functions
                try {
                    const owner = await tokenizedCash.getOwner();
                    console.log("   ✅ getOwner():", owner);
                } catch (e2) {
                    console.log("   ❌ getOwner() also failed");
                }
            }
            
            // Test mint function (might not exist)
            try {
                // First check if mint function exists without calling it
                console.log("   🔍 Checking if mint function exists...");
                const mintFunction = tokenizedCash.interface.getFunction('mint');
                console.log("   ✅ mint function signature:", mintFunction.format());
            } catch (e) {
                console.log("   ❌ mint function does not exist in ABI");
            }
            
        } catch (error) {
            console.log("❌ Failed to attach TokenizedCash contract:", error.message);
        }

        // Inspect AtomicSwap contract
        console.log("\n\n🔄 ATOMIC SWAP CONTRACT INSPECTION");
        console.log("===================================");
        console.log("Address:", ATOMIC_SWAP_ADDRESS);
        
        try {
            const AtomicSwap = await ethers.getContractFactory("AtomicSwap");
            const atomicSwap = AtomicSwap.attach(ATOMIC_SWAP_ADDRESS);
            
            console.log("\n📋 Available functions from ABI:");
            const abi = AtomicSwap.interface;
            
            // List all functions
            Object.keys(abi.functions).forEach(func => {
                console.log(`   - ${func}`);
            });
            
            // Test swapCounter function
            try {
                const counter = await atomicSwap.swapCounter();
                console.log("   ✅ swapCounter():", counter.toString());
            } catch (e) {
                console.log("   ❌ swapCounter() failed:", e.message);
                
                // Try alternative counter functions
                try {
                    const counter = await atomicSwap.counter();
                    console.log("   ✅ counter():", counter.toString());
                } catch (e2) {
                    try {
                        const counter = await atomicSwap.swapCount();
                        console.log("   ✅ swapCount():", counter.toString());
                    } catch (e3) {
                        console.log("   ❌ No counter function found");
                    }
                }
            }
            
        } catch (error) {
            console.log("❌ Failed to attach AtomicSwap contract:", error.message);
        }

        // Check if contracts exist at addresses (have code)
        console.log("\n\n🔍 CONTRACT CODE VERIFICATION");
        console.log("==============================");
        
        const tokenCode = await deployer.provider.getCode(TOKENIZED_CASH_ADDRESS);
        const swapCode = await deployer.provider.getCode(ATOMIC_SWAP_ADDRESS);
        
        console.log("TokenizedCash has code:", tokenCode !== "0x" ? "✅ YES" : "❌ NO");
        console.log("AtomicSwap has code:", swapCode !== "0x" ? "✅ YES" : "❌ NO");
        
        if (tokenCode === "0x") {
            console.log("⚠️  TokenizedCash address has no contract code!");
        }
        
        if (swapCode === "0x") {
            console.log("⚠️  AtomicSwap address has no contract code!");
        }

    } catch (error) {
        console.error("❌ Inspection failed:", error);
    }
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error(error);
        process.exit(1);
    });