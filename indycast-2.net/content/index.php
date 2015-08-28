<?
include_once('../indycast.net/common.php');
?>
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
