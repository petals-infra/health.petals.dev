$(() => {
  $(".show-full-peer-id").click(event => {
    $(".show-full-peer-id").text($(".show-full-peer-id").first().text() == "full" ? "short" : "full");
    $(".short-peer-id, .peer-id").toggle();
    event.preventDefault();
  });
  $(".explain-precision").click(event => {
    alert(
      'This column shows torch data type used for computation and ' +
      'quantization mode used for storing compressed weights.'
    );
    event.preventDefault();
  });
  $(".explain-adapters").click(event => {
    alert(
      'This column shows LoRA adapters pre-loaded by the server. ' +
      'A client may use one of these adapters if it wants to.\n\n' +
      'To add adapters to your server, pass `--adapters repo_name` argument. ' +
      'To use them in a client, set `AutoDistributedModel.from_pretrained(..., active_adapter="repo_name")` ' +
      'when you create a distributed model.'
    );
    event.preventDefault();
  });
  $(".explain-cache").click(event => {
    alert(
      'This column shows the number of available attention cache tokens (per block). ' +
      'If it is low, inference requests may be delayed or rejected.'
    );
    event.preventDefault();
  });
  $(".explain-avl").click(event => {
    alert(
      'This column shows whether a server is reachable directly or ' +
      'we need to use libp2p relays to traverse NAT/firewalls and reach it. ' +
      'Servers available through relays are usually slower, ' +
      'so we don\'t store DHT keys on them.'
    );
    event.preventDefault();
  });
  $(".explain-pings").click(event => {
    alert(
      'Press show to see round trip times (pings) from this server to next ones ' +
      'in a potential chain. This is used to find the fastest chain for inferene.'
    );
    event.preventDefault();
  });

  $('.ping .show').click(function (e) {
    e.preventDefault();

    $('.ping .show').hide();
    $(this).siblings('.hide').show();
    $(`.ping .rtt[data-source-id=${$(this).parent().data("peer-id")}]`).show();
  });
  $('.ping .hide').click(function (e) {
    e.preventDefault();

    $('.ping .hide, .ping .rtt').hide();
    $('.ping .show').show();
  });
});