
App.factory('Events', function(RESTService, $rootScope, localStorageService, $q, $timeout){
    var events = localStorageService.get('events');
    var cacheTimestamp = undefined;
    return {
        get: function () {
            if (checkCacheRefresh(cacheTimestamp)){
                cacheTimestamp = moment();
            RESTService.post(ENDPOINTS_DOMAIN + '/_ah/api/netegreek/v1/event/get_events', '')
                .success(function(data){
                    if (!RESTService.hasErrors(data)){
                        if (events != JSON.parse(data.data)){
                            events = JSON.parse(data.data);
                            localStorageService.set('events', events);
                            $rootScope.$broadcast('events:updated');

                        }
                    }
                    else{
                        console.log('ERROR: ',data);
                    }
                })
                .error(function(data) {
                    console.log('Error: ' , data);
                });
            }
            return events;
        },
        clear: function(){
            events = undefined;
        },
        refresh: function(){
            cacheTimestamp = undefined;
            this.get();
        },
        check: function(){
            if (events == null){
                this.get();
                return false;
            }
            return true;
        }
    };
});

/*
Everything gets a loading directive around it.
when getting data, we need a list that holds all data that is being queried


*/