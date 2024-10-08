document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('chat-form');
    const chatHistory = document.getElementById('chat-history');
    const questionInput = document.getElementById('question');
    const walletBalanceElement = document.getElementById('wallet-balance');

    marked.setOptions({
        highlight: function(code, lang) {
            const language = hljs.getLanguage(lang) ? lang : 'plaintext';
            return hljs.highlight(code, { language }).value;
        },
        langPrefix: 'hljs language-'
    });

    function displayBalanceInfo(finalBalance, balanceDifference) {
        console.log('Displaying balance info:', finalBalance, balanceDifference);
        const costDisplay = balanceDifference > 0 ? ` <span class="text-red-500 ml-1">(-${balanceDifference} sats)</span>` : '';
        walletBalanceElement.innerHTML = `Wallet Balance: ${finalBalance} sats${costDisplay}`;
    }

    async function fetchWalletBalance(lastCallCost = 0) {
        try {
            const response = await fetch('/get_balance');
            const data = await response.json();
            if (response.ok) {
                console.log('Fetched balance:', data.balance);
                displayBalanceInfo(data.balance, lastCallCost);
            } else {
                walletBalanceElement.textContent = 'Wallet Balance: Error fetching balance';
            }
        } catch (error) {
            walletBalanceElement.textContent = 'Wallet Balance: Error fetching balance';
            console.error('Error fetching wallet balance:', error);
        }
    }

    // Fetch wallet balance on page load
    fetchWalletBalance();

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const question = questionInput.value.trim();
        questionInput.value = ''; // Clear the input field immediately

        if (!question) {
            showError('Please enter a question.');
            return;
        }

        addMessageToChat('user', question);
        const loadingIndicator = addLoadingIndicator();

        try {
            const response = await fetch('/ask', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ question }),
            });

            const data = await response.json();
            loadingIndicator.remove();

            if (response.ok) {
                addMessageToChat('ai', data.answer);
                console.log('Received balance data:', data.final_balance, data.balance_difference);
                displayBalanceInfo(data.final_balance, data.balance_difference);
            } else {
                showError(data.error || 'An error occurred while processing your request.');
            }
        } catch (error) {
            loadingIndicator.remove();
            showError(`Network error: ${error.message}. Please check your internet connection and try again.`);
        }
    });

    function addMessageToChat(role, content) {
        const messageElement = document.createElement('div');
        messageElement.classList.add('max-w-[80%]', 'mb-5', 'p-3', 'rounded-2xl', 'text-base', 'leading-normal', 'break-words', 'animate-fadeIn');
        
        if (role === 'user') {
            messageElement.classList.add('self-end', 'bg-user-msg', 'text-white', 'rounded-br-none');
            messageElement.textContent = content;
        } else if (role === 'ai') {
            messageElement.classList.add('self-start', 'bg-ai-msg', 'text-[#ececf1]', 'rounded-bl-none');
            messageElement.innerHTML = marked.parse(content);
            messageElement.querySelectorAll('pre code').forEach((block) => {
                block.classList.add('bg-[#2d2d2d]', 'rounded', 'p-2.5', 'overflow-x-auto', 'font-mono', 'text-sm');
                hljs.highlightElement(block);
            });
            messageElement.querySelectorAll('p').forEach((p) => {
                p.classList.add('mb-2.5');
            });
        }
        
        chatHistory.appendChild(messageElement);
        scrollToBottom();
    }

    function showError(message) {
        const errorElement = document.createElement('div');
        errorElement.classList.add('self-center', 'bg-red-100', 'text-red-700', 'border', 'border-red-200', 'p-2.5', 'mb-4', 'rounded', 'max-w-[80%]');
        errorElement.textContent = message;
        chatHistory.appendChild(errorElement);
        scrollToBottom();
    }

    function addLoadingIndicator() {
        const loadingElement = document.createElement('div');
        loadingElement.classList.add('self-start', 'bg-ai-msg', 'text-[#ececf1]', 'p-3', 'rounded-2xl', 'text-base', 'mb-5', 'rounded-bl-none', 'animate-pulse');
        loadingElement.textContent = 'Thinking';
        chatHistory.appendChild(loadingElement);
        scrollToBottom();
        return loadingElement;
    }

    function scrollToBottom() {
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }
});
