// Script to list all available contract factories
const { ethers } = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
    console.log("🔍 Checking available contracts...\n");

    // Check contracts directory
    console.log("📁 CONTRACT FILES:");
    console.log("==================");
    const contractsDir = path.join(__dirname, "..", "contracts");
    
    if (fs.existsSync(contractsDir)) {
        const files = fs.readdirSync(contractsDir, { recursive: true });
        files.forEach(file => {
            if (file.endsWith('.sol')) {
                console.log(`   📄 ${file}`);
            }
        });
    } else {
        console.log("   ❌ No contracts directory found");
    }

    // Check artifacts directory (compiled contracts)
    console.log("\n🏗️  COMPILED ARTIFACTS:");
    console.log("=======================");
    const artifactsDir = path.join(__dirname, "..", "artifacts", "contracts");
    
    if (fs.existsSync(artifactsDir)) {
        function listArtifacts(dir, prefix = "") {
            const items = fs.readdirSync(dir);
            items.forEach(item => {
                const fullPath = path.join(dir, item);
                if (fs.statSync(fullPath).isDirectory()) {
                    console.log(`   📁 ${prefix}${item}/`);
                    listArtifacts(fullPath, prefix + "  ");
                } else if (item.endsWith('.json') && !item.endsWith('.dbg.json')) {
                    console.log(`   📄 ${prefix}${item}`);
                }
            });
        }
        listArtifacts(artifactsDir);
    } else {
        console.log("   ❌ No artifacts directory found");
    }

    // Try to get some common contract names
    console.log("\n🧪 TESTING COMMON CONTRACT NAMES:");
    console.log("==================================");
    
    const contractNames = [
        "TokenizedCash",
        "AtomicSwap", 
        "ERC20",
        "Token",
        "Cash",
        "Swap",
        "MyToken",
        "TestToken",
        "USDC",
        "MockERC20"
    ];

    for (const name of contractNames) {
        try {
            const factory = await ethers.getContractFactory(name);
            console.log(`   ✅ ${name} - Available`);
            
            // Show some function signatures
            const functions = Object.keys(factory.interface.functions).slice(0, 5);
            console.log(`      Functions: ${functions.join(', ')}${functions.length >= 5 ? '...' : ''}`);
        } catch (error) {
            console.log(`   ❌ ${name} - Not found`);
        }
    }

    // Check if we can interact with deployed contracts using generic interface
    console.log("\n🔍 GENERIC CONTRACT INSPECTION:");
    console.log("===============================");
    
    const TOKENIZED_CASH_ADDRESS = "0xF5f0b6c754226E67B723226C72d9451f9E2b68B5";
    const ATOMIC_SWAP_ADDRESS = "0xdF65C3d00b1021Fd667831D79915cB0321915AbC";
    
    const [deployer] = await ethers.getSigners();
    
    // Try to call basic ERC20 functions directly
    console.log("TokenizedCash at:", TOKENIZED_CASH_ADDRESS);
    try {
        // Create a generic contract instance with common ERC20 ABI
        const erc20Abi = [
            "function name() view returns (string)",
            "function symbol() view returns (string)", 
            "function decimals() view returns (uint8)",
            "function totalSupply() view returns (uint256)",
            "function balanceOf(address) view returns (uint256)",
            "function allowance(address,address) view returns (uint256)",
            "function approve(address,uint256) returns (bool)",
            "function transfer(address,uint256) returns (bool)"
        ];
        
        const token = new ethers.Contract(TOKENIZED_CASH_ADDRESS, erc20Abi, deployer);
        
        const name = await token.name();
        const symbol = await token.symbol();
        const decimals = await token.decimals();
        const totalSupply = await token.totalSupply();
        
        console.log(`   ✅ Name: ${name}`);
        console.log(`   ✅ Symbol: ${symbol}`);
        console.log(`   ✅ Decimals: ${decimals}`);
        console.log(`   ✅ Total Supply: ${ethers.formatUnits(totalSupply, decimals)}`);
        
    } catch (error) {
        console.log("   ❌ Failed to read as ERC20:", error.message);
    }
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error(error);
        process.exit(1);
    });