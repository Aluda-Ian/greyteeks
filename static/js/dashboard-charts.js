document.addEventListener("DOMContentLoaded", function() {
    const chartContainer = document.getElementById('campaignChart');
    if (!chartContainer) return;

    // Safely pull Django data from HTML attributes
    const campaignData = parseInt(chartContainer.getAttribute('data-campaigns')) || 0;
    const ctx = chartContainer.getContext('2d');

    new Chart(ctx, {
        type: 'line',
        data: {
            labels: ['Week 1', 'Week 2', 'Week 3', 'Current'],
            datasets: [{
                label: 'Campaign Activity',
                data: [5, 12, 8, campaignData],
                borderColor: '#3182ce',
                fill: true,
                backgroundColor: 'rgba(49, 130, 206, 0.1)',
                tension: 0.4
            }]
        },
        options: { responsive: true, maintainAspectRatio: false }
    });
});