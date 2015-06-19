#!/usr/bin/env ruby
require 'builder'

def product_xml
  xml = Builder::XmlMarkup.new( :indent => 2 )
  xml.rss( "xmlns:dc" => "http://purl.org/dc/elements/1.1/", 
           "xmlns:media" => "http://search.yahoo.com/mrss/",
           "xmlns:itunes" => "http://www.itunes.com/dtds/podcast-1.0.dtd", 
           "xmlns:feedburner" => "http://rssnamespace.org/feedburner/ext/1.0",
           "version" => "2.0",
           "xml:base" => "http://www.againstthegrain.org"
         ) do

    xml.channel do | channel |
      channel.title "Some title"
      channel.link "http://somelink"
      channel.description "Some desc"
      channel.language "en"
      channel.atom10 :link, {
        "xmlns:atom10" => "http://www.w3.org/2005/Atom",
        "rel" =>  "self",
        "type" => "application/rss+xml", 
        "href" => "http://feeds.feedburner.com/AgainstTheGrainHighQualityPodcast"
      }                    

      2.times do
        channel.item do | episode |
          episode.title "Some Title"
          episode.link "some linke"
          episode.description "some description"
          episode.pubDate "some date"
          episode.media :content, {
            "url" => "someurl",
            "fileSize" => 123,
            "type" => "audio/mpeg"
          } 
        end
      end
    end
  end
end

puts product_xml
