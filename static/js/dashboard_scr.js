
    // Fetch employee data
    fetch('/get_employees')
      .then(response => response.json())
      .then(data => {
        updateDashboard(data);
      });

    function updateDashboard(employees) {
      // Update counts
      document.getElementById('totalEmployees').textContent = employees.length;

      const positiveStates = ['happy', 'excited', 'engaged'];
      const concernStates = ['stressed', 'tired', 'anxious', 'sad', 'angry', 'frustrated'];

      const positiveCount = employees.filter(e =>
        positiveStates.includes(e.emotion?.toLowerCase())
      ).length;

      const concernCount = employees.filter(e =>
        concernStates.includes(e.emotion?.toLowerCase())
      ).length;

      document.getElementById('positiveCount').textContent = positiveCount;
      document.getElementById('concernCount').textContent = concernCount;

      // Update table
      const tableBody = document.getElementById('employeeTable');
      tableBody.innerHTML = '';

      employees.forEach(emp => {
        const row = document.createElement('tr');

        // Determine emotion color
        let emotionColor = 'text-gray-600';
        if (positiveStates.includes(emp.emotion?.toLowerCase())) emotionColor = 'text-green-600';
        if (concernStates.includes(emp.emotion?.toLowerCase())) emotionColor = 'text-amber-600';

        row.innerHTML = `
                    <td class="px-6 py-4 whitespace-nowrap">
                        <div class="flex items-center">
                            <div class="flex-shrink-0 h-10 w-10">
                                <img class="h-10 w-10 rounded-full" src="${emp.image || 'https://ui-avatars.com/api/?name=' + emp.name}" alt="">
                            </div>
                            <div class="ml-4">
                                <div class="text-sm font-medium text-gray-900">${emp.name}</div>
                                <div class="text-sm text-gray-500">${emp.position}</div>
                            </div>
                        </div>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap">
                        <span class="${emotionColor} font-medium capitalize">${emp.emotion || 'Not analyzed'}</span>
                    </td>
                    <td class="px-6 py-4 text-sm text-gray-500">
                        ${emp.recommendation || 'No recommendation yet'}
                    </td>
                `;
        tableBody.appendChild(row);
      });

      // Create chart
      const emotionCounts = employees.reduce((acc, emp) => {
        const emotion = emp.emotion ? emp.emotion.toLowerCase() : 'unknown';
        acc[emotion] = (acc[emotion] || 0) + 1;
        return acc;
      }, {});

      const ctx = document.getElementById('emotionChart').getContext('2d');
      new Chart(ctx, {
        type: 'doughnut',
        data: {
          labels: Object.keys(emotionCounts),
          datasets: [{
            data: Object.values(emotionCounts),
            backgroundColor: [
              '#3B82F6', '#10B981', '#F59E0B', '#EF4444',
              '#8B5CF6', '#EC4899', '#6EE7B7', '#FBBF24'
            ]
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { position: 'right' }
          }
        }
      });
    }