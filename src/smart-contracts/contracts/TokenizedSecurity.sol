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

    // Compliance restrictions
    mapping(address => bool) private _blacklisted;

    constructor(uint256 initialSupply) {
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(ISSUER_ROLE, msg.sender);
        _mint(msg.sender, initialSupply * (10 ** decimals));
    }

    // ===================== ERC20 Core =====================
    function totalSupply() public view override returns (uint256) {
        return _totalSupply;
    }

    function balanceOf(address account) public view override returns (uint256) {
        return _balances[account];
    }

    function transfer(address recipient, uint256 amount) public override returns (bool) {
        require(!_blacklisted[msg.sender] && !_blacklisted[recipient], "Compliance: address restricted");
        _transfer(msg.sender, recipient, amount);
        return true;
    }

    function allowance(address owner, address spender) public view override returns (uint256) {
        return _allowances[owner][spender];
    }

    function approve(address spender, uint256 amount) public override returns (bool) {
        require(!_blacklisted[spender], "Compliance: address restricted");
        _allowances[msg.sender][spender] = amount;
        emit Approval(msg.sender, spender, amount);
        return true;
    }

    function transferFrom(address sender, address recipient, uint256 amount) public override returns (bool) {
        require(!_blacklisted[sender] && !_blacklisted[recipient], "Compliance: address restricted");
        require(_allowances[sender][msg.sender] >= amount, "Allowance exceeded");

        _allowances[sender][msg.sender] -= amount;
        _transfer(sender, recipient, amount);
        return true;
    }

    // ===================== Internal Transfer =====================
    function _transfer(address from, address to, uint256 amount) internal {
        require(_balances[from] >= amount, "Insufficient balance");

        _balances[from] -= amount;
        _balances[to] += amount;

        emit Transfer(from, to, amount);
    }

    function _mint(address to, uint256 amount) internal {
        _balances[to] += amount;
        _totalSupply += amount;

        emit Transfer(address(0), to, amount);
    }

    // ===================== Compliance Admin Functions =====================
    function blacklist(address user) external onlyRole(COMPLIANCE_ROLE) {
        _blacklisted[user] = true;
    }

    function whitelist(address user) external onlyRole(COMPLIANCE_ROLE) {
        _blacklisted[user] = false;
    }

    function isBlacklisted(address user) external view returns (bool) {
        return _blacklisted[user];
    }

    // ===================== Issuer Minting (Optional) =====================
    function mint(address to, uint256 amount) external onlyRole(ISSUER_ROLE) {
        _mint(to, amount);
    }
}
