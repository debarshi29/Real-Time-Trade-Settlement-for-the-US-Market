// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

interface IERC20 {
    function transferFrom(address sender, address recipient, uint256 amount) external returns (bool);
}

contract AtomicSwap {
    function executeSwap(
        address tokenA, address tokenB,
        address partyA, address partyB,
        uint256 amountA, uint256 amountB
    ) external {
        require(IERC20(tokenA).transferFrom(partyA, partyB, amountA), "Token A transfer failed");
        require(IERC20(tokenB).transferFrom(partyB, partyA, amountB), "Token B transfer failed");
    }
}
