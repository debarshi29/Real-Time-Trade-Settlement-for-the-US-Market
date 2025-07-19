// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";

contract TokenizedSecurity is IERC20, AccessControl {
    string public constant name = "TokenizedSecurity";
    string public constant symbol = "TSEC";
    uint8 public constant decimals = 18;

    bytes32 public constant ISSUER_ROLE = keccak256("ISSUER_ROLE");
    bytes32 public constant COMPLIANCE_ROLE = keccak256("COMPLIANCE_ROLE");

    uint256 private _totalSupply;
    mapping(address => uint256) private _balances;
    mapping(address => mapping(address => uint256)) private _allowances;
    mapping(address => bool) private _blacklisted;

    constructor(uint256 initialSupply) {
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(ISSUER_ROLE, msg.sender);
        _mint(msg.sender, initialSupply * 1e18);
    }

    function totalSupply() public view override returns (uint256) {
        return _totalSupply;
    }

    function balanceOf(address account) public view override returns (uint256) {
        return _balances[account];
    }

    function transfer(address recipient, uint256 amount) public override returns (bool) {
        _beforeTokenTransfer(msg.sender, recipient, amount);
        _transfer(msg.sender, recipient, amount);
        return true;
    }

    function allowance(address owner, address spender) public view override returns (uint256) {
        return _allowances[owner][spender];
    }

    function approve(address spender, uint256 amount) public override returns (bool) {
        require(!_blacklisted[spender], "Blacklisted");
        _allowances[msg.sender][spender] = amount;
        emit Approval(msg.sender, spender, amount);
        return true;
    }

    function transferFrom(address sender, address recipient, uint256 amount) public override returns (bool) {
        require(_allowances[sender][msg.sender] >= amount, "Allowance too low");
        _beforeTokenTransfer(sender, recipient, amount);
        _allowances[sender][msg.sender] -= amount;
        _transfer(sender, recipient, amount);
        return true;
    }

    function _transfer(address from, address to, uint256 amount) internal {
        require(_balances[from] >= amount, "Not enough balance");
        _balances[from] -= amount;
        _balances[to] += amount;
        emit Transfer(from, to, amount);
    }

    function _mint(address to, uint256 amount) internal {
        _beforeTokenTransfer(address(0), to, amount);
        _balances[to] += amount;
        _totalSupply += amount;
        emit Transfer(address(0), to, amount);
    }

    function mint(address to, uint256 amount) external onlyRole(ISSUER_ROLE) {
        _mint(to, amount);
    }

    function blacklist(address user) external onlyRole(COMPLIANCE_ROLE) {
        _blacklisted[user] = true;
    }

    function whitelist(address user) external onlyRole(COMPLIANCE_ROLE) {
        _blacklisted[user] = false;
    }

    function isBlacklisted(address user) external view returns (bool) {
        return _blacklisted[user];
    }

    // ✅ No override — just check and use manually
    function _beforeTokenTransfer(address from, address to, uint256 amount) internal view {
        require(!_blacklisted[from] && !_blacklisted[to], "Blacklisted");
    }
}
