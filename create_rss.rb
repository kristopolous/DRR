#!/usr/bin/env ruby
require 'builder'

def product_xml
  xml = Builder::XmlMarkup.new( :indent => 2 )
  xml.instruct! :xml, :encoding => "ASCII"
  xml.product do |p|
    p.name "Test"
  end
end

puts product_xml
