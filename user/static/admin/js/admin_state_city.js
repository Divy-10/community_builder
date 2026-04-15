// State-City cascading dropdown for Django Admin
(function() {
    'use strict';

    function init() {
        var stateSelect = document.getElementById('id_state_select');
        var citySelect = document.getElementById('id_cityid');

        if (!stateSelect || !citySelect) {
            // Retry after a short delay (Django admin may load elements late)
            setTimeout(init, 500);
            return;
        }

        // Save the currently selected city (for edit mode)
        var currentCityId = citySelect.value;

        stateSelect.addEventListener('change', function() {
            loadCities(stateSelect.value, null);
        });

        // If state is already selected (edit mode), load cities and pre-select
        if (stateSelect.value) {
            loadCities(stateSelect.value, currentCityId);
        }

        function loadCities(stateId, preselectCityId) {
            // Clear city dropdown
            citySelect.innerHTML = '<option value="">---------</option>';

            if (!stateId) {
                return;
            }

            fetch('/api/cities/' + stateId + '/')
                .then(function(response) { return response.json(); })
                .then(function(data) {
                    citySelect.innerHTML = '<option value="">---------</option>';
                    data.forEach(function(c) {
                        var opt = document.createElement('option');
                        opt.value = c.cityid;
                        opt.textContent = c.cityname;
                        if (preselectCityId && String(c.cityid) === String(preselectCityId)) {
                            opt.selected = true;
                        }
                        citySelect.appendChild(opt);
                    });
                });
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
