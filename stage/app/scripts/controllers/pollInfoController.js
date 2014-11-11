    App.controller('pollInfoController', function($scope, $http, Load, $rootScope, $stateParams) {
        routeChange();
        Load.then(function(){
            $scope.loading = true;
            $rootScope.requirePermissions(MEMBER);
            var to_send = {key: $stateParams.key};
            $http.post(ENDPOINTS_DOMAIN + '/_ah/api/netegreek/v1/poll/get_poll_info', packageForSending(to_send))
                .success(function(data){
                    if (!checkResponseErrors(data)){
                        $scope.poll = JSON.parse(data.data);
                        $scope.creator = $rootScope.getUserFromKey($scope.poll.creator);
                    }
                    else{
                        $scope.notFound = true;
                        console.log('ERR');
                    }
                    $scope.loading = false;
                })
                .error(function(data) {
                    $scope.notFound = true;
                    console.log('Error: ' , data);
                    $scope.loading = false;
                });
        });
        $scope.closePoll = function(close){
            var to_send = {key: $stateParams.key};
            if (close === true){
                to_send.close = true;
            }
            else if (close === false){
                to_send.open = true;
            }
            $http.post(ENDPOINTS_DOMAIN + '/_ah/api/netegreek/v1/poll/edit_poll', packageForSending(to_send))
                .success(function(data){
                    if (!checkResponseErrors(data)){
                        if (close){
                            $scope.poll.open = false
                        }
                        else if (close === false){
                            $scope.poll.open = true;
                        }
                    }
                    else{
                        console.log('ERR');
                    }
                })
                .error(function(data) {
                    console.log('Error: ' , data);
                });
        }
        $scope.$watchCollection('poll.questions', function(){
            console.log('Im doing stuff');
            if ($scope.poll && $scope.poll.questions){   
            for (var i = 0; i < $scope.poll.questions.length; i++){
                if (!$scope.poll.questions[i].new_response){
                    $scope.formUnfinished = true;
                    return;
                }
            }
            $scope.formUnfinished = false;}
        })
        
//        #FIXME creator undefined :-P
        
        $scope.deletePoll = function(){
            var to_send = {key: $stateParams.key};
            $http.post(ENDPOINTS_DOMAIN + '/_ah/api/netegreek/v1/poll/delete', packageForSending(to_send))
                .success(function(data){
                    if (!checkResponseErrors(data)){
                        window.location.assign('#/app/polls')
                    }
                    else{
                        console.log('ERR');
                    }
                })
                .error(function(data) {
                    console.log('Error: ' , data);
                });
        }
        
        $scope.submitResponse = function(){
            var to_send = $scope.poll;
            $http.post(ENDPOINTS_DOMAIN + '/_ah/api/netegreek/v1/poll/answer_questions', packageForSending(to_send))
                .success(function(data){
                    if (!checkResponseErrors(data)){
                       window.location.assign('#/app/polls/'+$stateParams.key + '/results');
                    }
                    else{
                        console.log('ERR');
                    }
                })
                .error(function(data) {
                    console.log('Error: ' , data);
                });
        }
        
        $scope.goToResults = function(){
            window.location.assign('#/app/polls/'+$stateParams.key + '/results');
        }
	});