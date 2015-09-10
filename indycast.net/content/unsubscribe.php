<meta name="description" content="Sending you audio for later enjoyment" />
<link rel="stylesheet" href="/assets/css/main.css" />
<link href='http://fonts.googleapis.com/css?family=Inconsolata' rel='stylesheet' type='text/css'>
<link href='http://fonts.googleapis.com/css?family=Lora' rel='stylesheet' type='text/css'>
<link rel="stylesheet" href="/assets/css/reminder.css" />
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
        <label for='input'>Message (optional)</label>
        <textarea id='input' name='input'></textarea>

      </div>
      <div class="content">
        <div id="text-container">

          <label id='email-label' for="email">Your Email</label>
          <div>
            <input id='email-input' type='email' name='email'>
          </div>

          <label for="notes">Show Notes</label>
          <div>
            <input type='text' name='notes' placeholder="To help remember what this is">
          </div>
        </div>
        <div id='podcast-url-container'>
          <div id="thanks">Thanks, we'll notify you when the show is over and ready for download.</div>
          <div id="err">Woops, unable to register this reminder. Please try again. If the problem persists, <a href=mailto:indycast@googlegroups.com>Email us</a> with details.</div>
          <a class='big-button disabled'>
            <span id='rss-top'>
              <div id='rss-img'>
                <i class="fa fa-envelope"></i>
              </div>
              <div id='rss-header'>
                <h3 id='rss-title'>Email me the MP3</h3>
              </div>
            </span>
          </a>
        </div>
      </div>
    </section>
  </div>
</div>
<?= $emit_script ?>
<!--[if lte IE 8]><script src="/assets/js/ie/respond.min.js"></script><![endif]-->
