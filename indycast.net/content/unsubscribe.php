<link rel="stylesheet" href="/assets/css/main.css" />
<link href='http://fonts.googleapis.com/css?family=Inconsolata' rel='stylesheet' type='text/css'>
<link href='http://fonts.googleapis.com/css?family=Lora' rel='stylesheet' type='text/css'>
<link rel="stylesheet" href="/assets/css/reminder.css" />
<title>indycast | unsubscribe</title>

<style>
p{margin-bottom:0.5em;}
textarea { border: 1px solid #ccc; border-radius: 3; padding: 0.5em; width: 100% }
</style>

<div id="main">
  <h1>Unsubscribe from weekly emails</h1>

  <div class="box alt container">
    <section class="feature left">
      <div class="content">
        <p>Sorry to see you go. I'd like to understand why are leaving.</p>
        <p>I'll take your input into serious consideration. Thanks.</p>

        <p><small>~chris - founder of indycast</small></p>

      </div>
      <div class="content">
        <div id="text-container">
          <label style='width:auto' for='input'>Optional Message</label>
          <textarea id='input' name='input'></textarea>

          <div style='margin-top:0.5em'>
            <label id='email-label' for="email">Your Email</label>
            <div id='email-wrap'>
              <input id='email' type='email' name='email'>
            </div>
          </div>

        </div>
        <div id='podcast-url-container'>
          <div id="thanks">Thanks, you've been removed.</div>
          <div id="err">Woops, unable to unsubscribe this email address. Please try again. If the problem persists, <a href=mailto:indycast@googlegroups.com>Email us</a> with details.</div>
          <a id='stopit' class='button disabled'>Stop The Emails</a>
        </div>
      </div>
    </section>
  </div>
</div>
<?= $emit_script ?>
<!--[if lte IE 8]><script src="/assets/js/ie/respond.min.js"></script><![endif]-->
<script>
$(function() {
  ev(<?= json_encode($_GET); ?>);
  easy_bind(['email','input']);

  ev('', function(p) {
    $("#stopit")[p.email ? 'removeClass' : 'addClass']('disabled');
  });

  $("#stopit").click(function(){
    if(ev('email')) {
      $("#stopit").slideUp();
      remote('unsubscribe', ev('')).then(function(){
        $("#thanks").slideDown();
      }).fail(function(){
        $("#err").slideDown();
      });
    }
  });
});
</script>
