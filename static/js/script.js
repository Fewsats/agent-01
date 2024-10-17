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

    let conversationHistory = [];

    function displayBalanceInfo(finalBalance, balanceDifference, currency) {
        console.log('Displaying balance info:', finalBalance, balanceDifference, currency);
        const costDisplay = balanceDifference > 0 ? ` <span class="text-red-500 ml-1">(-${balanceDifference.toFixed(2)} ${currency})</span>` : '';
        walletBalanceElement.innerHTML = `Wallet Balance: ${finalBalance.toFixed(2)} ${currency} ${costDisplay}`;
    }

    async function fetchWalletBalance() {
        try {
            const response = await fetch('/get_balance');
            const data = await response.json();
            if (response.ok) {
                console.log('Fetched balance:', data.balance, data.currency);
                displayBalanceInfo(data.balance, 0, data.currency);
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

    // Function to auto-resize textarea
    function autoResizeTextarea() {
        questionInput.style.height = 'auto';
        questionInput.style.height = (questionInput.scrollHeight) + 'px';
        
        // Limit to 13 lines
        const lineHeight = parseInt(window.getComputedStyle(questionInput).lineHeight);
        const maxHeight = lineHeight * 13;
        if (questionInput.scrollHeight > maxHeight) {
            questionInput.style.height = maxHeight + 'px';
            questionInput.style.overflowY = 'auto';
        } else {
            questionInput.style.overflowY = 'hidden';
        }
    }

    // Add event listener for input changes
    questionInput.addEventListener('input', autoResizeTextarea);

    // Handle keydown event for shift+enter
    questionInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            form.dispatchEvent(new Event('submit'));
        }
    });

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const question = questionInput.value.trim();
        questionInput.value = ''; // Clear the input field immediately
        questionInput.style.height = 'auto'; // Reset height
        
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
                body: JSON.stringify({ question: question }),
            });

            const data = await response.json();
            loadingIndicator.remove();

            if (response.ok) {
                addMessageToChat('ai', data.answer);
                console.log('Received balance data:', data.final_balance, data.balance_difference, data.currency);
                displayBalanceInfo(data.final_balance, data.balance_difference, data.currency);
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
        messageElement.classList.add('max-w-[80%]', 'mb-5', 'p-5', 'rounded-2xl', 'text-base', 'leading-normal', 'break-words', 'animate-fadeIn', 'whitespace-pre-wrap');
        
        if (role === 'user') {
            messageElement.classList.add('self-end', 'bg-user-msg', 'text-black', 'rounded-br-none');
            messageElement.textContent = content;
        } else if (role === 'ai') {
            messageElement.classList.add('self-start', 'bg-white', 'text-black', 'rounded-bl-none');
            messageElement.innerHTML = marked.parse(content);
            messageElement.querySelectorAll('pre code').forEach((block) => {
                block.classList.add('bg-[#2d2d2d]', 'rounded', 'p-2.5', 'overflow-x-auto', 'font-mono', 'text-sm', 'text-white');
                hljs.highlightElement(block);
            });
            messageElement.querySelectorAll('p').forEach((p) => {
                p.classList.add('mb-2.5');
            });
        }
        
        chatHistory.appendChild(messageElement);
        scrollToBottom();

        conversationHistory.push({ role, content });
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
        loadingElement.classList.add('self-start', 'bg-white', 'text-black', 'p-5', 'rounded-2xl', 'text-base', 'mb-5', 'rounded-bl-none', 'animate-pulse');
        loadingElement.textContent = 'Thinking';
        chatHistory.appendChild(loadingElement);
        scrollToBottom();
        return loadingElement;
    }

    function scrollToBottom() {
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }

    const sendSmsButton = document.getElementById('send-sms');
    const accessWebsiteButton = document.getElementById('access-website');

    function setPrompt(prompt) {
        const currentValue = questionInput.value;
        const separator = currentValue && !currentValue.endsWith('\n') ? '\n' : '';
        questionInput.value = currentValue + separator + prompt;
        autoResizeTextarea();
        questionInput.focus();
    }

    sendSmsButton.addEventListener('click', () => {
        setPrompt("Tool to send SMS: l402://api.fewsats.com/v0/gateway/d4a9eff9-991f-4664-ab0e-d9add4597c76/info");
    });

    accessWebsiteButton.addEventListener('click', () => {
        setPrompt("Tool to scrape websites: l402://api.fewsats.com/v0/gateway/f12e5deb-b07b-4af4-a4f2-3fbf076228a9/info");
    });

    async function sendPrompt(prompt) {
        autoResizeTextarea();
        
        addMessageToChat('user', prompt);
        const loadingIndicator = addLoadingIndicator();

        try {
            const response = await fetch('/ask', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ question: prompt }),
            });

            const data = await response.json();
            loadingIndicator.remove();

            if (response.ok) {
                addMessageToChat('ai', data.answer);
                console.log('Received balance data:', data.final_balance, data.balance_difference, data.currency);
                displayBalanceInfo(data.final_balance, data.balance_difference, data.currency);
            } else {
                showError(data.error || 'An error occurred while processing your request.');
            }
        } catch (error) {
            loadingIndicator.remove();
            showError(`Network error: ${error.message}. Please check your internet connection and try again.`);
        }

        questionInput.value = ''; // Clear the input field after sending
        autoResizeTextarea();
    }

});
