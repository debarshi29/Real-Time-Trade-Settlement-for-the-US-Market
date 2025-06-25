// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

interface IERC20 {
    function transferFrom(address from, address to, uint256 value) external returns (bool);
}

contract AtomicSwap {
    struct Trade {
        address seller;
        address buyer;
        address tokenSell;
        address tokenBuy;
        uint256 amountSell;
        uint256 amountBuy;
        bool sellerApproved;
        bool buyerApproved;
        bool executed;
    }

    uint256 public tradeCounter;
    mapping(uint256 => Trade) public trades;

    event TradeInitialized(uint256 tradeId, address seller, address buyer);
    event TradeApproved(uint256 tradeId, address approver);
    event TradeExecuted(uint256 tradeId);

    // Step 1: Create a trade agreement
    function initTrade(
        address seller,
        address buyer,
        address tokenSell,
        uint256 amountSell,
        address tokenBuy,
        uint256 amountBuy
    ) external returns (uint256) {
        trades[tradeCounter] = Trade(
            seller,
            buyer,
            tokenSell,
            tokenBuy,
            amountSell,
            amountBuy,
            false,
            false,
            false
        );
        emit TradeInitialized(tradeCounter, seller, buyer);
        return tradeCounter++;
    }

    // Step 2: Approvals from both sides
    function approveTrade(uint256 tradeId) external {
        Trade storage t = trades[tradeId];
        require(!t.executed, "Trade already executed");
        require(msg.sender == t.seller || msg.sender == t.buyer, "Not part of this trade");

        if (msg.sender == t.seller) t.sellerApproved = true;
        if (msg.sender == t.buyer) t.buyerApproved = true;

        emit TradeApproved(tradeId, msg.sender);
    }

    // Step 3: Execute the trade atomically
    function executeTrade(uint256 tradeId) external {
        Trade storage t = trades[tradeId];
        require(!t.executed, "Already executed");
        require(t.sellerApproved && t.buyerApproved, "Trade not fully approved");

        require(
            IERC20(t.tokenSell).transferFrom(t.seller, t.buyer, t.amountSell),
            "Token A transfer failed"
        );
        require(
            IERC20(t.tokenBuy).transferFrom(t.buyer, t.seller, t.amountBuy),
            "Token B transfer failed"
        );

        t.executed = true;
        emit TradeExecuted(tradeId);
    }
}
