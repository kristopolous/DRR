<?
include_once('../indycast.net/common.php');
?>
<!DOCTYPE html>
<html lang="en">

<head>

    <meta charset="utf-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="description" content="">
    <meta name="author" content="">

    <title>Indycast - A technology to record the radio that doesn't get podcasted</title>

    <link href="/css/bootstrap.min.css" rel="stylesheet">
    <link href="/css/sb-admin.css" rel="stylesheet">
    <link href="/font-awesome/css/font-awesome.min.css" rel="stylesheet" type="text/css">

    <!-- HTML5 Shim and Respond.js IE8 support of HTML5 elements and media queries -->
    <!-- WARNING: Respond.js doesn't work if you view the page via file:// -->
    <!--[if lt IE 9]>
        <script src="https://oss.maxcdn.com/libs/html5shiv/3.7.0/html5shiv.js"></script>
        <script src="https://oss.maxcdn.com/libs/respond.js/1.4.2/respond.min.js"></script>
    <![endif]-->

</head>
<body>
  <div id="wrapper">
    <nav class="navbar navbar-inverse navbar-fixed-top" role="navigation">
      <div class="navbar-header">
        <button type="button" class="navbar-toggle" data-toggle="collapse" data-target=".navbar-ex1-collapse">
          <span class="sr-only">Toggle navigation</span>
          <span class="icon-bar"></span>
          <span class="icon-bar"></span>
          <span class="icon-bar"></span>
        </button>
        <a class="navbar-brand" href="index.html">Indycast - record the radio that doesn't get podcasted</a>
      </div>

      <div class="collapse navbar-collapse navbar-ex1-collapse">
        <ul class="nav navbar-nav side-nav">
          <li class="active"><a href="index.html"><i class="fa fa-fw fa-calendar"></i> Free Podcasts</a></li>
          <li><a href="charts.html"><i class="fa fa-fw fa-pencil-square-o"></i> Email Me Radio</a></li>
          <li><a href="tables.html"><i class="fa fa-fw fa-clock-o"></i> Listen Live</a></li>
          <li><a href="forms.html"><i class="fa fa-fw fa-book"></i> Our Story</a></li>
          <li><a href="https://github.com/kristopolous/DRR/wiki/Donating-Money"><i class="fa fa-fw fa-heart"></i> Support Us</a></li>
          <li><a href="https://github.com/kristopolous/DRR"><i class="fa fa-fw fa-code"></i> Source Code</a></li>
        </ul>
      </div>
    </nav>

    <div id="page-wrapper">
      <div class="container-fluid">
        <div class="row">
          <div class="col-lg-12">
            <h1 class="page-header">
              A DVR for Radio <small>easy, free, open source.</small>
            </h1>
          </div>
        </div>

        <div class="row">
          <div class="col-lg-4">
            <div class="panel panel-default">
              <div class="panel-heading">
                <h3 class="panel-title">1. Pick a Station</h3>
              </div>
              <div class="panel-body">
                <div class="list-group"><?
                  foreach(active_stations() as $station) {
                    echo '<a desc="' . $station['description'] . '" class="list-group-item button">' . ($station['callsign']) . '</a>';
                  }?>
                </div>
                <div class="text-right">
                  <a href="#">Volunteer to Add a Station <i class="fa fa-arrow-circle-right"></i></a>
                </div>
              </div>
            </div>
          </div>
          <div class="col-lg-8">
            <div class="panel panel-default">
              <div class="panel-heading">
                <h3 class="panel-title">Step 2. Time to Record</h3>
              </div>
              <div class="panel-body">
                <div class="content" id='day-picker'>

                 <div class="form-group">
                    <label for="day">Day of week to record on</label><br/>
                    <div class="btn-group week-group" id="day" role="group">
                      <button type="button" class="btn btn-default">sun</button>
                      <button type="button" class="btn btn-default">mon</button>
                      <button type="button" class="btn btn-default">tue</button>
                      <button type="button" class="btn btn-default">wed</button>
                      <button type="button" class="btn btn-default">thu</button>
                      <button type="button" class="btn btn-default">fri</button>
                      <button type="button" class="btn btn-default">sat</button>
                    </div>
                  </div>

                  <div id='time' class='form-group'>
                    <label for="start">Starting at</label>
                    <div id='time-controls'>
                      <div class="input-group input-group-lg inline">
                        <input class="text form-control" size="4" type="text" name="start" id="start" value="" placeholder="ex: 3:30 PM" />
                        <div class="btn-group week-group inline" id="ampm" role="group">
                          <button type="button" class="btn btn-default">am</button>
                          <button type="button" class="btn btn-default">pm</button>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div class="form-group">
                    <label for="duration">For how long</label><br/>
                    <div class="week-group btn-group" id="duration">
                      <button data="30" type="button" class="btn btn-default">30</button>
                      <button data="1hr" type="button" class="btn btn-default">1hr</button>
                      <button data="1hr30" type="button" class="btn btn-default">1&frac12; hrs</button>
                      <button data="2hr" type="button" class="btn btn-default">2hr</button>
                    </div>
                  </div>
                </div>

                <div class="form-group content">
                  <label for='name'>Give it a name</label>
                  <div class="input-group input-group-lg">
                    <input class="text form-control" type="text" name="name" id="name" value="" placeholder="ex. Alien Air Music" />
                  </div>
                </div>
             </div>
            </div>
            <div class="panel panel-default">
              <div class="panel-heading">
                <h3 class="panel-title">Step 3. You're Done</h3>
              </div>
              <div class="panel-body">
                <h3>My free subscription</h3>
                <a id="podcast-url" class='big-button disabled'></a>
                <div class="panel panel-green">
                  <div class="panel-heading">
                    <div class="row">
                      <div class="col-xs-3">
                        <i class="fa fa-tasks fa-5x"></i>
                      </div>
                      <div class="col-xs-9 text-right">
                        <div class="huge">12</div>
                        <div>New Tasks!</div>
                      </div>
                    </div>
                  </div>
                  <a href="#">
                    <div class="panel-footer">
                      <span class="pull-left">View Details</span>
                      <span class="pull-right"><i class="fa fa-arrow-circle-right"></i></span>
                      <div class="clearfix"></div>
                    </div>
                  </a>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
  <script src="/js/evda.min.js"></script>
  <script src="/js/jquery.js"></script>
  <script src="/js/bootstrap.min.js"></script>
</body>
</html>
